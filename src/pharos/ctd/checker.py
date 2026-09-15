"""Compare a dossier outline against the ICH M4 CTD structure and score completeness.

Input outline (YAML or JSON), either a dict::

    product: "Examplimab 100 mg"
    applicant: "Pharos Pharma"
    region: "US"                 # selects the Module 1 variant; default US
    sections:
      - id: "2.5"
        title: "Clinical Overview"
        status: complete         # complete | draft | missing   (default complete)
        pages: 48
      - id: "3.2.S.4"
        ...

or simply a list of section ids / entries.

Scoring is a weighted share of *required* leaf sections present per module. ``draft``
counts half. Sections listed in the outline that are not in the spec, or that name a
parent (e.g. "4.2.3 Toxicology") instead of its leaves, become warnings.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

SPEC_PATH = Path(__file__).resolve().parent / "data" / "ich_m4_ctd.yaml"

STATUS_SCORE = {
    "complete": 1.0,
    "completed": 1.0,
    "final": 1.0,
    "done": 1.0,
    "present": 1.0,
    "draft": 0.5,
    "in_progress": 0.5,
    "in progress": 0.5,
    "partial": 0.5,
    "missing": 0.0,
    "planned": 0.0,
    "todo": 0.0,
    "not_started": 0.0,
}

SEVERITY_BY_WEIGHT = {3: "critical", 2: "major", 1: "minor"}
TITLE_MATCH_THRESHOLD = 0.86


# ------------------------------------------------------------------ spec model


@dataclass
class SpecSection:
    id: str
    title: str
    module: str
    required: bool = False
    weight: int = 1
    note: str = ""
    children: list["SpecSection"] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def norm_id(self) -> str:
        return normalize_id(self.id)


@dataclass
class SpecModule:
    id: str
    title: str
    note: str
    regional: bool
    sections: list[SpecSection]

    def leaves(self) -> Iterator[SpecSection]:
        yield from _iter_leaves(self.sections)

    def parents(self) -> Iterator[SpecSection]:
        yield from _iter_parents(self.sections)


def _build_sections(raw: list[dict], module_id: str) -> list[SpecSection]:
    out = []
    for item in raw:
        children = _build_sections(item.get("children", []), module_id)
        out.append(
            SpecSection(
                id=str(item["id"]),
                title=str(item.get("title", "")),
                module=module_id,
                required=bool(item.get("required", False)),
                weight=int(item.get("weight", 1)),
                note=str(item.get("note", "") or ""),
                children=children,
            )
        )
    return out


def _iter_leaves(sections: list[SpecSection]) -> Iterator[SpecSection]:
    for s in sections:
        if s.is_leaf:
            yield s
        else:
            yield from _iter_leaves(s.children)


def _iter_parents(sections: list[SpecSection]) -> Iterator[SpecSection]:
    for s in sections:
        if not s.is_leaf:
            yield s
            yield from _iter_parents(s.children)


def available_regions(path: Path = SPEC_PATH) -> list[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    for m in raw["modules"]:
        if m.get("variants"):
            return sorted(m["variants"].keys())
    return []


def load_spec(region: str | None = "US", path: Path = SPEC_PATH) -> list[SpecModule]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    region = (region or "US").upper()
    modules: list[SpecModule] = []
    for m in raw["modules"]:
        mid = str(m["id"])
        if m.get("variants"):
            if region not in m["variants"]:
                raise ValueError(f"Unknown region '{region}'. Available: {sorted(m['variants'])}")
            sections = _build_sections(m["variants"][region], mid)
        else:
            sections = _build_sections(m.get("sections", []), mid)
        modules.append(
            SpecModule(
                id=mid,
                title=str(m["title"]),
                note=str(m.get("note", "") or ""),
                regional=bool(m.get("regional", False)),
                sections=sections,
            )
        )
    return modules


# ------------------------------------------------------------------ outline parsing


def normalize_id(raw: Any) -> str:
    s = str(raw).strip().upper()
    s = re.sub(r"^(MODULE|MOD\.?|M)\s*", "", s)
    s = re.sub(r"\s+", "", s)
    s = s.rstrip(".")
    return s


def normalize_title(raw: Any) -> str:
    s = str(raw).lower()
    s = re.sub(r"\(.*?\)", " ", s)  # drop parenthetical detail
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


@dataclass
class OutlineEntry:
    id: str | None
    title: str | None
    status: str
    pages: int | None
    raw: Any


def _coerce_entry(item: Any) -> OutlineEntry:
    if isinstance(item, dict):
        sid = item.get("id") or item.get("section") or item.get("number")
        title = item.get("title") or item.get("name")
        status = str(item.get("status", "complete") or "complete").strip().lower()
        pages = item.get("pages")
        return OutlineEntry(
            id=str(sid) if sid is not None else None,
            title=str(title) if title else None,
            status=status,
            pages=int(pages) if isinstance(pages, (int, float)) else None,
            raw=item,
        )
    # bare string: "3.2.P.8 Stability" or just "3.2.P.8"
    text = str(item).strip()
    m = re.match(r"^([0-9][0-9A-Za-z.]*)\s*[-–:]?\s*(.*)$", text)
    if m:
        return OutlineEntry(id=m.group(1), title=m.group(2) or None, status="complete", pages=None, raw=item)
    return OutlineEntry(id=None, title=text, status="complete", pages=None, raw=item)


def parse_outline(obj: Any) -> tuple[dict, list[OutlineEntry]]:
    """Return (metadata, entries) from a dict-with-sections or a plain list."""
    if isinstance(obj, dict):
        meta = {k: v for k, v in obj.items() if k != "sections"}
        items = obj.get("sections", [])
    else:
        meta, items = {}, obj
    return meta, [_coerce_entry(i) for i in items or []]


def load_outline(path: str | Path) -> Any:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


# ------------------------------------------------------------------ results


@dataclass
class Gap:
    section_id: str
    title: str
    module: str
    weight: int
    severity: str
    status: str  # "missing" | "draft"
    note: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModuleScore:
    module_id: str
    title: str
    score: float  # 0..1 weighted
    required_total: int
    required_present: int
    required_draft: int
    optional_missing: list[str]
    gaps: list[Gap]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["gaps"] = [g.as_dict() for g in self.gaps]
        d["score_pct"] = round(self.score * 100, 1)
        return d


@dataclass
class CTDCheckResult:
    product: str
    region: str
    overall_score: float
    ready_to_submit: bool
    modules: list[ModuleScore]
    gaps: list[Gap]
    warnings: list[str]
    unmatched_entries: list[str]
    matched_sections: int
    spec_version: str

    def as_dict(self) -> dict:
        return {
            "product": self.product,
            "region": self.region,
            "spec_version": self.spec_version,
            "overall_score": self.overall_score,
            "overall_score_pct": round(self.overall_score * 100, 1),
            "ready_to_submit": self.ready_to_submit,
            "n_gaps": len(self.gaps),
            "n_critical_gaps": sum(1 for g in self.gaps if g.severity == "critical"),
            "modules": [m.as_dict() for m in self.modules],
            "gaps": [g.as_dict() for g in self.gaps],
            "warnings": self.warnings,
            "unmatched_entries": self.unmatched_entries,
            "matched_sections": self.matched_sections,
        }


# ------------------------------------------------------------------ the check


def check_outline(outline: Any, region: str | None = None, spec_path: Path = SPEC_PATH) -> CTDCheckResult:
    meta, entries = parse_outline(outline)
    region = (region or meta.get("region") or "US").upper()
    modules = load_spec(region, spec_path)
    spec_version = yaml.safe_load(spec_path.read_text(encoding="utf-8")).get("version", "")

    leaves_by_id: dict[str, SpecSection] = {}
    parents_by_id: dict[str, SpecSection] = {}
    for m in modules:
        for leaf in m.leaves():
            leaves_by_id[leaf.norm_id] = leaf
        for parent in m.parents():
            parents_by_id[parent.norm_id] = parent
    title_index = {normalize_title(l.title): l for l in leaves_by_id.values()}
    title_keys = list(title_index.keys())

    matched: dict[str, OutlineEntry] = {}
    warnings: list[str] = []
    unmatched: list[str] = []

    for e in entries:
        leaf: SpecSection | None = None
        nid = normalize_id(e.id) if e.id else None
        if nid and nid in leaves_by_id:
            leaf = leaves_by_id[nid]
        elif nid and nid in parents_by_id:
            parent = parents_by_id[nid]
            warnings.append(
                f"'{e.id}' ({parent.title}) is listed as a single section, but the CTD requires its "
                f"sub-sections individually ({', '.join(c.id for c in parent.children)}). Expand it."
            )
            continue
        elif e.title:
            key = normalize_title(e.title)
            if key in title_index:
                leaf = title_index[key]
            else:
                close = difflib.get_close_matches(key, title_keys, n=1, cutoff=TITLE_MATCH_THRESHOLD)
                if close:
                    leaf = title_index[close[0]]
                    warnings.append(f"Matched '{e.title}' to {leaf.id} {leaf.title} by title similarity — confirm.")
        if leaf is None:
            unmatched.append(f"{e.id or ''} {e.title or ''}".strip())
            continue
        if leaf.norm_id in matched:
            warnings.append(f"Section {leaf.id} appears more than once in the outline.")
        matched[leaf.norm_id] = e

    module_scores: list[ModuleScore] = []
    all_gaps: list[Gap] = []
    total_weight = 0.0
    total_earned = 0.0

    for m in modules:
        req = [l for l in m.leaves() if l.required]
        opt = [l for l in m.leaves() if not l.required]
        w_total = sum(l.weight for l in req)
        earned = 0.0
        present = draft = 0
        gaps: list[Gap] = []
        for leaf in req:
            entry = matched.get(leaf.norm_id)
            s = STATUS_SCORE.get(entry.status, 1.0) if entry else 0.0
            earned += leaf.weight * s
            if s >= 1.0:
                present += 1
            else:
                status = "draft" if (entry and s > 0) else "missing"
                if status == "draft":
                    draft += 1
                gaps.append(
                    Gap(
                        section_id=leaf.id,
                        title=leaf.title,
                        module=m.id,
                        weight=leaf.weight,
                        severity=SEVERITY_BY_WEIGHT.get(leaf.weight, "minor"),
                        status=status,
                        note=leaf.note,
                    )
                )
        optional_missing = [f"{l.id} {l.title}" for l in opt if l.norm_id not in matched]
        score = earned / w_total if w_total else 1.0
        module_scores.append(
            ModuleScore(
                module_id=m.id,
                title=m.title,
                score=score,
                required_total=len(req),
                required_present=present,
                required_draft=draft,
                optional_missing=optional_missing,
                gaps=gaps,
            )
        )
        all_gaps.extend(gaps)
        total_weight += w_total
        total_earned += earned

    overall = total_earned / total_weight if total_weight else 1.0
    severity_rank = {"critical": 0, "major": 1, "minor": 2}
    all_gaps.sort(key=lambda g: (severity_rank[g.severity], g.status != "missing", g.module, g.section_id))

    return CTDCheckResult(
        product=str(meta.get("product") or meta.get("name") or "Unnamed product"),
        region=region,
        overall_score=overall,
        ready_to_submit=not all_gaps,
        modules=module_scores,
        gaps=all_gaps,
        warnings=warnings,
        unmatched_entries=unmatched,
        matched_sections=len(matched),
        spec_version=str(spec_version),
    )


# ------------------------------------------------------------------ helpers for users


def outline_template(region: str = "US", status: str = "missing", include_optional: bool = True) -> dict:
    """A blank outline listing every CTD leaf, ready for a regulatory team to fill in."""
    modules = load_spec(region)
    sections = []
    for m in modules:
        for leaf in m.leaves():
            if not leaf.required and not include_optional:
                continue
            sections.append(
                {
                    "id": leaf.id,
                    "title": leaf.title,
                    "status": status,
                    "required": leaf.required,
                }
            )
    return {"product": "<product name>", "applicant": "<applicant>", "region": region, "sections": sections}
