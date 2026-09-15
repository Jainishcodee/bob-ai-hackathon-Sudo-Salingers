"""Pharos MCP server — exposes the evidence layer to IBM Bob.

Bob connects to this server over MCP (Model Context Protocol) and gains six tools. The
division of labour is deliberate:

    Pharos (this server)  → numbers, tables, structured gaps. Deterministic, testable.
    IBM Bob               → reads the evidence, reasons over it, writes the narrative:
                            "here is the signal, here is why it matters, here is who
                            should look at it next" / "here is the remediation order for
                            the dossier gaps".

Remove Bob and the product loses its conversational interface and its explanations —
that is what makes the integration load-bearing rather than decorative.

Run:   python -m mcp_server.server          (stdio transport, what Bob expects)
See:   docs/bob-integration.md for registering it in Bob and example prompts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:  # mcp >= 2.0 renamed FastMCP → MCPServer; decorators (.tool/.resource/.prompt/.run) are unchanged
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP

# Allow `python mcp_server/server.py` as well as `python -m mcp_server.server`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pharos import __version__  # noqa: E402
from pharos.ctd.checker import check_outline, load_outline, load_spec, outline_template  # noqa: E402
from pharos.ctd.report import gap_report_markdown  # noqa: E402
from pharos.faers.client import OpenFDAClient  # noqa: E402
from pharos.signals.cluster import cluster_signals  # noqa: E402
from pharos.signals.detector import compute_pair, scan_drug  # noqa: E402
from pharos.signals.stats import SignalCriteria  # noqa: E402
from pharos.signals.timeline import signal_timeline  # noqa: E402

load_dotenv()

mcp = FastMCP(
    "pharos",
    instructions=(
        "Pharos is a drug-safety evidence engine. Use scan_signals / compute_prr to get "
        "disproportionality statistics from real FDA FAERS data, cluster_signals to group them by "
        "organ system, and check_ctd_dossier to audit a regulatory dossier outline against ICH M4. "
        "The tools return numbers and structured gaps; YOU write the interpretation. Always state the "
        "case count, PRR with CI, and chi-square when describing a signal, and always caveat that "
        "spontaneous-report disproportionality shows association, not causation, and is subject to "
        "reporting biases (e.g. litigation-driven reporting, notoriety bias)."
    ),
)

_client: OpenFDAClient | None = None


def client() -> OpenFDAClient:
    global _client
    if _client is None:
        _client = OpenFDAClient()
    return _client


def _split_names(drug: str, aliases: str | list[str] | None) -> list[str]:
    names = [drug]
    if isinstance(aliases, str):
        names += [a for a in aliases.split(",") if a.strip()]
    elif aliases:
        names += list(aliases)
    return names


# ------------------------------------------------------------------ Mode 1: signal detection


@mcp.tool()
def scan_signals(
    drug: str,
    aliases: str = "",
    top_n: int = 50,
    min_cases: int = 3,
    prr_threshold: float = 2.0,
    chi2_threshold: float = 4.0,
    max_rows: int = 30,
) -> dict[str, Any]:
    """Disproportionality scan of one drug across every reaction reported with it in FDA FAERS.

    Returns reactions ranked with clinical signals first, each with case count (a), PRR + 95% CI,
    ROR + 95% CI, chi-square (Yates), signal flag under Evans (2001) criteria, a triage tier, and
    whether the term is administrative (e.g. DRUG INEFFECTIVE) rather than clinical.

    Args:
        drug: name as it appears in FAERS, e.g. "rofecoxib".
        aliases: comma-separated extra names to OR in — brand names matter a lot for older
                 drugs, e.g. "vioxx".
        top_n: how many of the drug's most-reported reactions to evaluate.
        min_cases / prr_threshold / chi2_threshold: signal criteria (defaults = Evans 2001).
        max_rows: cap on rows returned to keep the response readable.
    """
    criteria = SignalCriteria(min_cases=min_cases, prr_threshold=prr_threshold, chi2_threshold=chi2_threshold)
    res = scan_drug(_split_names(drug, aliases), client(), top_n=top_n, criteria=criteria)
    out = res.as_dict(top=max_rows)
    out["interpretation_notes"] = [
        "PRR/ROR measure disproportionality of *reporting*, not incidence or causation.",
        "Administrative terms are statistically evaluated but excluded from clinical signal counts.",
        "Large litigation or media events inflate reporting for specific drug–event pairs (notoriety bias).",
    ]
    return out


@mcp.tool()
def compute_prr(drug: str, reaction: str, aliases: str = "") -> dict[str, Any]:
    """Full 2x2 contingency analysis for ONE drug–reaction pair using an exact AND query.

    Returns the a/b/c/d table, PRR and ROR with 95% CIs, chi-square, the Evans signal verdict,
    and a one-line summary. Use this to verify or drill into a specific pair from scan_signals.
    """
    return compute_pair(_split_names(drug, aliases), reaction, client())


@mcp.tool()
def cluster_signals_by_organ_system(drug: str, aliases: str = "", top_n: int = 50) -> dict[str, Any]:
    """Group a drug's clinical signals by MedDRA System Organ Class (heuristic mapping).

    Useful for answering "is this a cardiac problem or a liver problem?" Returns one row per
    organ class with the number of signals, total cases, max PRR and the strongest reaction.
    The SOC assignment is a curated + keyword heuristic (MedDRA itself is licensed), so
    'curated_share' indicates how much of each cluster came from the verified map.
    """
    res = scan_drug(_split_names(drug, aliases), client(), top_n=top_n)
    cl = cluster_signals(res.table)
    return {
        "drug": res.drug,
        "reports_mentioning_drug": res.drug_reports,
        "n_clinical_signals": int(len(res.signals())),
        "clusters": cl.to_dict(orient="records"),
        "mapping_note": "System Organ Class assignment is heuristic; confirm against licensed MedDRA before regulatory use.",
    }


@mcp.tool()
def search_reports(drug: str, reaction: str = "", aliases: str = "", limit: int = 5) -> dict[str, Any]:
    """Fetch a few raw FAERS case reports for a drug (optionally with a specific reaction).

    Returns trimmed reports: report id, receive date, seriousness flags, patient age/sex,
    all reactions listed, and co-reported drugs. Use it to sanity-check a statistical signal
    against real case narratives before escalating.
    """
    reports = client().sample_reports(_split_names(drug, aliases), reaction or None, limit=min(limit, 20))
    return {"drug": drug.upper(), "reaction": reaction.upper() or None, "n": len(reports), "reports": reports}


@mcp.tool()
def signal_emergence_timeline(
    drug: str,
    reaction: str,
    aliases: str = "",
    exclude_drugs: str = "",
    start_year: int = 2004,
    end_year: int = 0,
    min_cases: int = 3,
    prr_threshold: float = 2.0,
    chi2_threshold: float = 4.0,
    detect_masking: bool = True,
) -> dict[str, Any]:
    """WHEN would this signal first have been flagged — and what masked it? Rebuilds the 2x2 table year by year.

    For each calendar year (by FDA receive date) returns the drug's report count, the drug∧reaction
    count, that year's PRR, and the CUMULATIVE PRR/chi-square using all reports the FDA had by
    31 December of that year — i.e. what a safety scientist running the screen then would have seen.
    Reports the first year the cumulative table met the signal criteria, real regulatory milestones
    for the drug (from data/samples/regulatory_actions.yaml, where known), and the lead time between them.

    MASKING: with detect_masking=True each year also lists the top drugs behind the reaction's reports
    ('top_contributor', 'top_contributor_share_pct', 'masking_alert' when one drug ≥ 25%). If one drug
    dominates, call again with exclude_drugs set to it: the tool removes those reports from the comparator
    background and returns a masking-corrected series ('cum_prr_adj', 'first_flag_year_masking_corrected').
    Example: rosiglitazone × MYOCARDIAL INFARCTION is masked by Vioxx litigation reports (~70% of all MI
    reports in 2005–06); exclude_drugs="rofecoxib, vioxx" moves first detection from 2008 to 2005.

    Args:
        drug / aliases / reaction: as in compute_prr.
        exclude_drugs: comma-separated drug names to remove from the background.
        start_year: openFDA data begins 2004; earlier years are ignored.
        end_year: 0 = current year. Narrow the range to save API requests (4–7 per year).
    """
    criteria = SignalCriteria(min_cases=min_cases, prr_threshold=prr_threshold, chi2_threshold=chi2_threshold)
    exclude = [e.strip() for e in exclude_drugs.split(",") if e.strip()] if exclude_drugs else None
    res = signal_timeline(_split_names(drug, aliases), reaction, client(), start_year=start_year, end_year=end_year or None,
                          criteria=criteria, exclude=exclude, detect_masking=detect_masking)
    return res.as_dict()


# ------------------------------------------------------------------ Mode 2: submission readiness


@mcp.tool()
def check_ctd_dossier(outline_path: str = "", outline_json: str = "", region: str = "") -> dict[str, Any]:
    """Audit a drug-approval dossier outline against the ICH M4 CTD structure.

    Provide EITHER outline_path (a YAML/JSON file on disk) OR outline_json (the outline as a JSON
    string). Returns per-module completeness scores, every gap in required sections ranked by
    severity (critical / major / minor) with a 'why it matters' note, warnings (e.g. a parent
    section listed instead of its sub-sections), unrecognised entries, and a ready-to-submit
    verdict. Also includes a Markdown gap report you can hand to the regulatory team.

    Args:
        outline_path: path to the outline file, e.g. "data/samples/dossier_incomplete.yaml".
        outline_json: alternative — the outline as JSON text.
        region: "US" or "EU" (selects Module 1 variant). Defaults to the outline's own region or US.
    """
    if outline_path:
        outline = load_outline(outline_path)
    elif outline_json:
        outline = json.loads(outline_json)
    else:
        raise ValueError("Provide outline_path or outline_json.")
    res = check_outline(outline, region=region or None)
    out = res.as_dict()
    out["markdown_report"] = gap_report_markdown(res)
    return out


@mcp.tool()
def get_ctd_spec(region: str = "US", as_blank_outline: bool = False) -> dict[str, Any]:
    """Return the ICH M4 CTD checklist Pharos uses (Modules 1–5 with required flags, weights, notes).

    Set as_blank_outline=True to get a fillable outline template instead — every section with
    status 'missing' — which a regulatory team can complete and feed back to check_ctd_dossier.
    """
    if as_blank_outline:
        return outline_template(region)
    modules = load_spec(region)

    def dump(s):
        return {
            "id": s.id,
            "title": s.title,
            "required": s.required,
            "weight": s.weight,
            "note": s.note,
            "children": [dump(c) for c in s.children],
        }

    return {
        "region": region.upper(),
        "modules": [
            {"id": m.id, "title": m.title, "note": m.note, "regional": m.regional, "sections": [dump(s) for s in m.sections]}
            for m in modules
        ],
    }


# ------------------------------------------------------------------ meta


@mcp.resource("pharos://about")
def about() -> str:
    return (
        f"Pharos v{__version__} — a lighthouse for drug safety.\n"
        "Mode 1: PRR/ROR/chi-square signal detection over openFDA FAERS (20M+ reports).\n"
        "Mode 2: ICH M4 CTD submission-readiness checking.\n"
        "Tools: scan_signals, compute_prr, cluster_signals_by_organ_system, search_reports, "
        "signal_emergence_timeline, check_ctd_dossier, get_ctd_spec."
    )


@mcp.prompt()
def signal_assessment(drug: str, aliases: str = "") -> str:
    """Prompt template: produce a pharmacovigilance signal assessment for a drug."""
    return (
        f"Run scan_signals for '{drug}' (aliases: '{aliases}'). Then, for the top 3 clinical signals, call "
        "compute_prr to confirm each with an exact query and search_reports to see 2–3 real cases. For the "
        "strongest signal call signal_emergence_timeline to establish when it first met the criteria. "
        "Write a signal assessment memo with: (1) BLUF — one sentence verdict; (2) a table of the top "
        "signals with n, PRR [CI], chi²; (3) organ-system grouping from cluster_signals_by_organ_system; "
        "(4) the emergence year of the lead signal and its lead time versus any regulatory action; "
        "(5) plausible reporting biases; (6) recommended next step (e.g. formal causality assessment, "
        "label review, no action). Never claim causation."
    )


@mcp.prompt()
def dossier_gap_memo(outline_path: str) -> str:
    """Prompt template: turn a CTD check into a remediation plan."""
    return (
        f"Call check_ctd_dossier with outline_path='{outline_path}'. Write a memo for the regulatory affairs "
        "lead: overall readiness verdict, module-by-module status, the critical gaps first with why each "
        "would cause a refuse-to-file or major deficiency, a recommended remediation order considering "
        "dependencies (e.g. 2.7 Clinical Summary depends on 5.3.5.3 integrated analyses), and which "
        "functional team owns each gap."
    )


if __name__ == "__main__":
    mcp.run()
