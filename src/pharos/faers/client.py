"""Thin client for the openFDA drug adverse-event endpoint (FAERS).

Why openFDA rather than the raw quarterly FAERS files: the ``count`` endpoint returns
the marginal totals we need for a 2x2 table in a handful of small requests, so there
is no multi-gigabyte download and the demo runs on live data.

Every response is cached to disk keyed by the request URL. With ``PHAROS_OFFLINE=1``
the client never touches the network and serves only from cache — the demo survives
a dead Wi-Fi connection. Run ``python -m pharos build-cache`` once online to warm it.

Rate limits (per openFDA docs): 240 requests/min; 1,000/day without a key,
120,000/day with a free key from https://open.fda.gov/apis/authentication/.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import httpx

OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "cache"

# Fields we match a drug name against. ``medicinalproduct`` is the verbatim name on the
# report (often a brand name in old reports, e.g. "VIOXX"); the ``openfda.*`` fields are
# FDA-harmonised names, present only when the product maps to a current label.
DRUG_FIELDS = (
    "patient.drug.medicinalproduct",
    "patient.drug.openfda.generic_name",
    "patient.drug.openfda.brand_name",
)
REACTION_FIELD = "patient.reaction.reactionmeddrapt"


class OpenFDAError(RuntimeError):
    """Any failure talking to openFDA."""


class OfflineCacheMiss(OpenFDAError):
    """Offline mode was requested and the response is not in the cache."""


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


class OpenFDAClient:
    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str | Path | None = None,
        offline: bool | None = None,
        timeout: float = 30.0,
        max_retries: int = 4,
    ):
        self.api_key = api_key or os.environ.get("OPENFDA_API_KEY") or None
        self.cache_dir = Path(cache_dir or os.environ.get("PHAROS_CACHE_DIR") or DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.offline = _env_flag("PHAROS_OFFLINE") if offline is None else offline
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_source: str = "none"  # "cache" | "live" — handy for the UI to display
        # openFDA serves `count` queries keyless only up to limit=500; 1000 needs a key.
        self.max_count_limit = 1000 if self.api_key else 500
        self._http = httpx.Client(timeout=timeout, headers={"User-Agent": "pharos/0.1"})

    # ------------------------------------------------------------------ plumbing

    @staticmethod
    def _build_url(params: dict[str, str], base: str = OPENFDA_EVENT_URL) -> str:
        # openFDA is particular about its query syntax: ``field:"term"`` with ``+`` as the
        # OR separator between terms. Percent-encode everything except the characters
        # that carry that syntax.
        safe_chars = ':+"()'
        parts = [f"{k}={quote(str(v), safe=safe_chars)}" for k, v in params.items()]
        return base + "?" + "&".join(parts)

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def _get(self, params: dict[str, str], base: str = OPENFDA_EVENT_URL, transform=None) -> dict:
        """GET with disk cache. ``transform`` (optional) shrinks the payload *before* it is cached —
        used for drug labels, which are ~100 KB each and would bloat the committed cache."""
        url = self._build_url(params, base)
        cache_file = self._cache_path(url)
        if cache_file.exists():
            self.last_source = "cache"
            return json.loads(cache_file.read_text(encoding="utf-8"))
        if self.offline:
            raise OfflineCacheMiss(
                f"PHAROS_OFFLINE is set and this query is not cached:\n  {url}\n"
                "Run `python -m pharos build-cache` while online, or unset PHAROS_OFFLINE."
            )

        request_url = url + (f"&api_key={self.api_key}" if self.api_key else "")
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http.get(request_url)
            except httpx.HTTPError as exc:
                if attempt == self.max_retries:
                    raise OpenFDAError(f"Network error calling openFDA: {exc}") from exc
                time.sleep(delay)
                delay *= 2
                continue

            if resp.status_code == 404:
                # openFDA returns 404 for "no matches" — that's a legitimate zero, not an error.
                data = {"meta": {"results": {"total": 0}}, "results": []}
                break
            if resp.status_code == 403 and self.api_key and "API_KEY_INVALID" in resp.text:
                # A bad key must never take the demo down: drop to keyless mode and retry once.
                import warnings

                warnings.warn("openFDA rejected OPENFDA_API_KEY — continuing keyless (500-term count cap).", stacklevel=2)
                self.api_key = None
                self.max_count_limit = 500
                request_url = url
                if params.get("count") and int(params.get("limit", "0") or 0) > 500:
                    params = {**params, "limit": "500"}
                    url = self._build_url(params, base)
                    cache_file = self._cache_path(url)
                    request_url = url
                continue
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            if resp.status_code != 200:
                raise OpenFDAError(f"openFDA returned HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            break

        if transform is not None:
            data = transform(data)
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        self.last_source = "live"
        return data

    # ------------------------------------------------------------------ query builders

    @staticmethod
    def drug_expression(names: str | Iterable[str]) -> str:
        """OR together every name across every drug-name field."""
        if isinstance(names, str):
            names = [names]
        terms = [f'{field}:"{n.strip().upper()}"' for n in names for field in DRUG_FIELDS if n.strip()]
        return "+".join(terms)

    @staticmethod
    def reaction_expression(reaction: str) -> str:
        # ``.exact`` matches the MedDRA preferred term exactly. The plain field is a phrase match —
        # "OEDEMA" would also hit OEDEMA PERIPHERAL, PULMONARY OEDEMA … (6x over-count) and would
        # disagree with the ``count`` endpoint, which always tallies exact terms.
        return f'{REACTION_FIELD}.exact:"{reaction.strip().upper()}"'

    @staticmethod
    def year_expression(year: int) -> str:
        """Reports FDA *received* in a calendar year — i.e. what was knowable by 31 Dec that year."""
        return f"receivedate:[{year}0101+TO+{year}1231]"

    @staticmethod
    def and_(*exprs: str) -> str:
        """AND expressions together; OR-lists get parenthesised, range queries are left bare."""

        def wrap(e: str) -> str:
            needs = "+" in e and not e.startswith("(") and "[" not in e
            return f"({e})" if needs else e

        return "+AND+".join(wrap(e) for e in exprs if e)

    def report_count(self, expr: str | None = None) -> int:
        """Number of reports matching an arbitrary search expression (None = everything)."""
        params = {"limit": "1"}
        if expr:
            params = {"search": expr, "limit": "1"}
        return int(self._get(params)["meta"]["results"]["total"])

    # ------------------------------------------------------------------ public API

    def total_reports(self) -> int:
        """Total adverse-event reports in openFDA (N for the 2x2 table)."""
        return int(self._get({"limit": "1"})["meta"]["results"]["total"])

    def drug_report_count(self, names: str | Iterable[str]) -> int:
        expr = self.drug_expression(names)
        return int(self._get({"search": expr, "limit": "1"})["meta"]["results"]["total"])

    def reaction_report_count(self, reaction: str) -> int:
        expr = self.reaction_expression(reaction)
        return int(self._get({"search": expr, "limit": "1"})["meta"]["results"]["total"])

    def drug_reaction_counts(self, names: str | Iterable[str], limit: int = 1000) -> list[dict]:
        """Reactions reported alongside the drug, most frequent first: [{term, count}, ...]."""
        expr = self.drug_expression(names)
        limit = min(limit, self.max_count_limit)
        data = self._get({"search": expr, "count": REACTION_FIELD + ".exact", "limit": str(limit)})
        return [{"term": r["term"], "count": int(r["count"])} for r in data.get("results", [])]

    def background_reaction_counts(self, limit: int = 1000) -> dict[str, int]:
        """Most frequent reactions across ALL of FAERS — the background rate in one request."""
        limit = min(limit, self.max_count_limit)
        data = self._get({"count": REACTION_FIELD + ".exact", "limit": str(limit)})
        return {r["term"]: int(r["count"]) for r in data.get("results", [])}

    def reaction_counts(self, expr: str | None = None, limit: int = 500) -> list[dict]:
        """Reaction term counts for ANY search expression (None = all of FAERS): [{term, count}, ...]."""
        params = {"count": REACTION_FIELD + ".exact", "limit": str(min(limit, self.max_count_limit))}
        if expr:
            params = {"search": expr, **params}
        data = self._get(params)
        return [{"term": r["term"], "count": int(r["count"])} for r in data.get("results", [])]

    @staticmethod
    def window_expression(start_year: int, end_year: int) -> str:
        """Reports FDA received between 1 Jan ``start_year`` and 31 Dec ``end_year`` inclusive."""
        return f"receivedate:[{start_year}0101+TO+{end_year}1231]"

    # ------------------------------------------------------------------ drug labels (SPL)

    LABEL_SECTIONS = (
        "boxed_warning", "warnings_and_cautions", "warnings", "contraindications", "precautions",
        "general_precautions", "adverse_reactions", "drug_interactions", "use_in_specific_populations", "overdosage",
    )

    @classmethod
    def _trim_labels(cls, data: dict) -> dict:
        out = []
        for r in data.get("results", []):
            fda = r.get("openfda", {}) or {}
            out.append(
                {
                    "brand_name": fda.get("brand_name", []),
                    "generic_name": fda.get("generic_name", []),
                    "substance_name": fda.get("substance_name", []),
                    "manufacturer_name": fda.get("manufacturer_name", []),
                    "product_type": fda.get("product_type", []),
                    "set_id": r.get("set_id"),
                    "effective_time": r.get("effective_time"),
                    "sections": {k: " ".join(r[k]) for k in cls.LABEL_SECTIONS if r.get(k)},
                }
            )
        return {"meta": data.get("meta", {}), "results": out}

    def label_documents(self, names: str | Iterable[str], limit: int = 15) -> list[dict]:
        """Current FDA-approved labels (SPL) for a drug, trimmed to the safety sections.

        Tries the harmonised generic, substance and brand name fields in turn. Returns [] when the
        product has no current label in openFDA — typical for withdrawn drugs, and informative in itself.
        """
        if isinstance(names, str):
            names = [names]
        names = [n.strip().upper() for n in names if n and n.strip()]
        for fld in ("openfda.generic_name", "openfda.substance_name", "openfda.brand_name"):
            expr = "+".join(f'{fld}:"{n}"' for n in names)
            data = self._get({"search": expr, "limit": str(limit)}, base=OPENFDA_LABEL_URL, transform=self._trim_labels)
            if data.get("results"):
                return data["results"]
        return []

    def drug_contributors(self, expr: str, limit: int = 8) -> list[dict]:
        """Which drugs appear most in the reports matching ``expr``? [{term, count}, ...].

        Used to detect *masking*: one drug's reporting wave (e.g. Vioxx litigation) can make up most
        of a reaction's background and hide the same signal for every other drug.
        """
        data = self._get({"search": expr, "count": "patient.drug.medicinalproduct.exact", "limit": str(min(limit, self.max_count_limit))})
        return [{"term": r["term"], "count": int(r["count"])} for r in data.get("results", [])]

    def drug_reaction_report_count(self, names: str | Iterable[str], reaction: str) -> int:
        """Reports mentioning BOTH the drug and the reaction (cell ``a``)."""
        expr = f"({self.drug_expression(names)})+AND+{self.reaction_expression(reaction)}"
        return int(self._get({"search": expr, "limit": "1"})["meta"]["results"]["total"])

    def sample_reports(self, names: str | Iterable[str], reaction: str | None = None, limit: int = 5) -> list[dict]:
        """A few raw reports, trimmed to the fields a reviewer actually reads."""
        expr = self.drug_expression(names)
        if reaction:
            expr = f"({expr})+AND+{self.reaction_expression(reaction)}"
        data = self._get({"search": expr, "limit": str(limit)})
        out = []
        for r in data.get("results", []):
            patient = r.get("patient", {})
            out.append(
                {
                    "safetyreportid": r.get("safetyreportid"),
                    "receivedate": r.get("receivedate"),
                    "serious": r.get("serious"),
                    "seriousnessdeath": r.get("seriousnessdeath"),
                    "seriousnesshospitalization": r.get("seriousnesshospitalization"),
                    "patient_age": patient.get("patientonsetage"),
                    "patient_sex": patient.get("patientsex"),
                    "reactions": [x.get("reactionmeddrapt") for x in patient.get("reaction", [])],
                    "drugs": [x.get("medicinalproduct") for x in patient.get("drug", [])][:8],
                }
            )
        return out

    def close(self) -> None:
        self._http.close()
