"""Pharos command-line interface.

    python -m pharos scan rofecoxib --alias vioxx
    python -m pharos prr rofecoxib "myocardial infarction"
    python -m pharos ctd-check data/samples/dossier_incomplete.yaml
    python -m pharos ctd-template --region EU > my_dossier.yaml
    python -m pharos build-cache
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pharos import __version__

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # src/.env, independent of the working directory

app = typer.Typer(
    help="Pharos — a lighthouse for drug safety. Signal detection over FDA FAERS + ICH M4 CTD readiness checks.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

SRC_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DEMO_DRUGS = SRC_DIR / "data" / "samples" / "demo_drugs.txt"


def _client():
    from pharos.faers.client import OpenFDAClient

    return OpenFDAClient()


def _fmt(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


# ---------------------------------------------------------------- scan


@app.command()
def scan(
    drug: str = typer.Argument(..., help="Drug name as it appears in FAERS, e.g. ROFECOXIB."),
    alias: list[str] = typer.Option([], "--alias", "-a", help="Extra names to OR in (brand names, salts). Repeatable."),
    top: int = typer.Option(50, help="How many of the drug's most-reported reactions to evaluate."),
    min_cases: int = typer.Option(3, help="Minimum case count for a signal (Evans: 3)."),
    prr_threshold: float = typer.Option(2.0, help="PRR threshold (Evans: 2.0)."),
    chi2_threshold: float = typer.Option(4.0, help="Chi-square threshold (Evans: 4.0)."),
    show_all: bool = typer.Option(False, "--all", help="Show every evaluated reaction, not just signals."),
    clusters: bool = typer.Option(True, help="Also show signals grouped by system organ class."),
    label: bool = typer.Option(True, "--label/--no-label", help="Check each signal against the current FDA label: already labelled, or new?"),
    json_out: Optional[Path] = typer.Option(None, "--json", help="Write the full result as JSON to this path."),
):
    """Disproportionality scan: every reaction reported with DRUG, ranked, signals flagged, checked against the FDA label."""
    from pharos.faers.client import OpenFDAError
    from pharos.signals.cluster import cluster_signals
    from pharos.signals.detector import scan_drug
    from pharos.signals.label import annotate_with_label, label_summary, load_label
    from pharos.signals.stats import SignalCriteria

    names = [drug, *alias]
    criteria = SignalCriteria(min_cases=min_cases, prr_threshold=prr_threshold, chi2_threshold=chi2_threshold)
    client = _client()
    with console.status(f"Querying openFDA for {', '.join(n.upper() for n in names)} …"):
        result = scan_drug(names, client, top_n=top, criteria=criteria)

    label_line = ""
    if label:
        try:
            with console.status("Fetching the current FDA label …"):
                lab = load_label(names, client)
            result.table = annotate_with_label(result.table, lab)
            ls = label_summary(result.table)
            if lab.found:
                label_line = (f"\nFDA label ({', '.join(lab.products[:2])}): [green]{ls['labelled']} already labelled[/green]"
                              f" ({ls['boxed_warning']} in the boxed warning) · [bold yellow]{ls['unlabelled']} NOT on the label[/bold yellow] → review these first")
            else:
                label_line = "\nFDA label: [dim]no current label in openFDA (withdrawn / discontinued product)[/dim]"
        except OpenFDAError as exc:
            label_line = f"\n[dim]FDA label check skipped: {str(exc).splitlines()[0]}[/dim]"

    console.print(
        Panel.fit(
            f"[bold]{result.drug}[/bold]  ·  {result.drug_reports:,} reports mention it  ·  "
            f"{result.total_reports:,} reports in FAERS  ·  source: openFDA ({result.source})\n"
            f"Criteria: n ≥ {criteria.min_cases}, PRR ≥ {criteria.prr_threshold}, χ² ≥ {criteria.chi2_threshold}   "
            f"→ [bold red]{len(result.signals())} clinical signals[/bold red] among {len(result.table)} reactions evaluated"
            + label_line,
            title="Pharos · signal scan",
        )
    )

    has_label = "label_status" in result.table.columns
    df = result.table if show_all else result.signals()
    t = Table(box=box.SIMPLE_HEAVY, show_lines=False)
    for col in ("Reaction", "n", "PRR", "95% CI", "ROR", "χ²", "Tier") + (("On FDA label?",) if has_label else ()) + ("Flags",):
        t.add_column(col, justify="right" if col in ("n", "PRR", "ROR", "χ²") else "left")
    for _, r in df.iterrows():
        flags = []
        if r["is_administrative"]:
            flags.append("admin")
        if r["haldane_corrected"]:
            flags.append("0.5-corr")
        style = "bold red" if (r["is_signal"] and not r["is_administrative"]) else ("dim" if not r["is_signal"] else "")
        cells = [r["reaction"], str(int(r["n_cases"])), _fmt(r["prr"]), f"{_fmt(r['prr_ci_low'])}–{_fmt(r['prr_ci_high'])}",
                 _fmt(r["ror"]), _fmt(r["chi2"], 1), r["tier"]]
        if has_label:
            sec = r["label_section"]
            cells.append("[bold yellow]NOT ON LABEL[/bold yellow]" if r["is_labelled"] is False else (f"[green]{sec}[/green]" if sec else "[dim]—[/dim]"))
        cells.append(",".join(flags))
        t.add_row(*cells, style=style)
    console.print(t)

    if clusters:
        cl = cluster_signals(result.table)
        if not cl.empty:
            ct = Table(title="Signals by system organ class (heuristic MedDRA SOC mapping)", box=box.SIMPLE)
            ct.add_column("System organ class")
            ct.add_column("Signals", justify="right")
            ct.add_column("Cases", justify="right")
            ct.add_column("Max PRR", justify="right")
            ct.add_column("Strongest reaction")
            for _, r in cl.iterrows():
                ct.add_row(r["soc"], str(r["n_reactions"]), str(r["n_cases"]), _fmt(r["max_prr"]), r["strongest_reaction"])
            console.print(ct)

    n_disagree = int((~result.table["methods_agree"]).sum()) if not result.table.empty else 0
    if n_disagree > 0:
        console.print(f"[dim]{n_disagree} reaction(s) where PRR and IC disagree[/dim]")
    if result.skipped_reactions:
        console.print(f"[dim]{len(result.skipped_reactions)} rare reactions skipped (request budget).[/dim]")
    if json_out:
        json_out.write_text(json.dumps(result.as_dict(), indent=2, default=str), encoding="utf-8")
        console.print(f"[green]Wrote {json_out}[/green]")


# ---------------------------------------------------------------- prr


@app.command()
def prr(
    drug: str = typer.Argument(...),
    reaction: str = typer.Argument(..., help='MedDRA preferred term, e.g. "MYOCARDIAL INFARCTION".'),
    alias: list[str] = typer.Option([], "--alias", "-a"),
    json_out: Optional[Path] = typer.Option(None, "--json"),
):
    """Full 2x2 analysis for one drug–reaction pair."""
    from pharos.signals.detector import compute_pair

    with console.status("Querying openFDA …"):
        res = compute_pair([drug, *alias], reaction, _client())

    tb = res["table"]
    grid = Table(box=box.SQUARE, title=f"2×2 table — {res['drug']} × {res['reaction']}")
    grid.add_column("")
    grid.add_column(res["reaction"], justify="right")
    grid.add_column("other reactions", justify="right")
    grid.add_row(res["drug"], f"a = {int(tb['a']):,}", f"b = {int(tb['b']):,}")
    grid.add_row("other drugs", f"c = {int(tb['c']):,}", f"d = {int(tb['d']):,}")
    console.print(grid)

    verdict = "[bold red]SIGNAL[/bold red]" if res["is_signal"] else "[green]no signal[/green]"
    who_verdict = "[bold red]SIGNAL[/bold red]" if res["is_signal_ic"] else "[green]no signal[/green]"
    console.print(
        Panel.fit(
            f"PRR = [bold]{res['prr']:.2f}[/bold]  (95% CI {res['prr_ci_low']:.2f}–{res['prr_ci_high']:.2f})\n"
            f"ROR = {res['ror']:.2f}  (95% CI {res['ror_ci_low']:.2f}–{res['ror_ci_high']:.2f})\n"
            f"χ² (Yates) = {res['chi2']:.1f}    cases = {res['n_cases']}\n"
            f"Evans 2001 criteria → {verdict}   tier: {res['tier']}\n"
            f"IC = {res['ic']:.2f}   IC025 = {res['ic025']:.2f}  → WHO rule: {who_verdict}"
            + ("\n[dim]Haldane 0.5 correction applied (zero cell).[/dim]" if res["haldane_corrected"] else "")
            + f"\n[dim]source: {res['data_source']}[/dim]",
            title="Disproportionality",
        )
    )
    if json_out:
        json_out.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
        console.print(f"[green]Wrote {json_out}[/green]")


# ---------------------------------------------------------------- hidden


@app.command()
def hidden(
    drug: str = typer.Argument(...),
    alias: list[str] = typer.Option([], "--alias", "-a"),
    as_of: Optional[int] = typer.Option(None, "--as-of", help="Use only reports FDA had received by 31 Dec of this year (default: today)."),
    start: int = typer.Option(2004, "--from"),
    top: int = typer.Option(60, help="Reactions to evaluate."),
    checks: int = typer.Option(30, help="How many of them to check for masking (1–3 requests each)."),
    min_share: float = typer.Option(25.0, help="A product holding at least this %% of a reaction's reports is treated as a masker."),
    min_cases: int = typer.Option(3),
    prr_threshold: float = typer.Option(2.0),
    chi2_threshold: float = typer.Option(4.0),
    json_out: Optional[Path] = typer.Option(None, "--json"),
):
    """Which signals is the standard screen HIDING? Automatic masking detection + correction across a whole drug."""
    from pharos.signals.masking import find_hidden_signals
    from pharos.signals.stats import SignalCriteria

    criteria = SignalCriteria(min_cases=min_cases, prr_threshold=prr_threshold, chi2_threshold=chi2_threshold)
    with console.status("Running the standard screen, then checking each reaction's background for a dominant product …"):
        res = find_hidden_signals([drug, *alias], _client(), as_of_year=as_of, start_year=start, top_n=top,
                                  max_checks=checks, min_share_pct=min_share, criteria=criteria)

    console.print(Panel.fit(res.headline(), title="Pharos · hidden signals", border_style="red" if len(res.unmasked) else "green"))
    shown = res.table[res.table["status"].isin(["unmasked", "strengthened", "masked, sub-threshold"])]
    if shown.empty:
        console.print("[green]No reaction had a single product holding a large share of its reports — the standard screen is not being distorted here.[/green]")
    else:
        t = Table(box=box.SIMPLE_HEAVY)
        for col, just in (("Reaction", "left"), ("n", "right"), ("PRR\nstandard", "right"), ("Signal?", "left"), ("Masking product\n(share of reaction's reports)", "left"),
                          ("PRR\ncorrected", "right"), ("χ²\ncorrected", "right"), ("Result", "left")):
            t.add_column(col, justify=just, no_wrap=(col != "Reaction"))
        style_by = {"unmasked": "bold red", "strengthened": "yellow", "masked, sub-threshold": "dim"}
        for _, r in shown.iterrows():
            t.add_row(r["reaction"], f"{int(r['n_cases']):,}", _fmt(r["prr_std"]), "yes" if r["signal_std"] else "no",
                      f"{r['maskers']} ({r['excluded_share_pct']:.0f}%)", _fmt(r["prr_adj"]) if pd_notna(r["prr_adj"]) else "—",
                      f"{r['chi2_adj']:,.0f}" if pd_notna(r["chi2_adj"]) else "—",
                      {"unmasked": "● HIDDEN SIGNAL", "strengthened": "▲ understated", "masked, sub-threshold": "masked, still < threshold"}[r["status"]],
                      style=style_by[r["status"]])
        console.print(t)
    console.print(f"[dim]Rule: exclude any single product with ≥ {min_share:.0f}% of a reaction's reports in the window, plus its known aliases. "
                  f"Window = FDA receive dates {res.start_year}–{res.end_year}. {res.reactions_checked} reactions checked. No analyst choice involved.[/dim]")
    if json_out:
        json_out.write_text(json.dumps(res.as_dict(), indent=2, default=str), encoding="utf-8")
        console.print(f"[green]Wrote {json_out}[/green]")


# ---------------------------------------------------------------- timeline


@app.command()
def timeline(
    drug: str = typer.Argument(...),
    reaction: str = typer.Argument(..., help='MedDRA preferred term, e.g. "MYOCARDIAL INFARCTION".'),
    alias: list[str] = typer.Option([], "--alias", "-a"),
    exclude: list[str] = typer.Option([], "--exclude", "-x", help="Product(s) to remove from the comparator background (masking correction). Repeatable. Use `-x auto` to let the ≥25%% share rule choose, prospectively (no look-ahead)."),
    start: int = typer.Option(2004, "--from", help="First year (openFDA data begins 2004)."),
    end: Optional[int] = typer.Option(None, "--to", help="Last year (default: current year)."),
    min_cases: int = typer.Option(3),
    prr_threshold: float = typer.Option(2.0),
    chi2_threshold: float = typer.Option(4.0),
    detect_masking: bool = typer.Option(True, help="List the top drugs behind the reaction's reports each year."),
    json_out: Optional[Path] = typer.Option(None, "--json"),
):
    """When would this signal first have been flagged — and what masked it? Yearly + cumulative PRR vs real regulatory dates."""
    from pharos.signals.stats import SignalCriteria
    from pharos.signals.timeline import MASKING_ALERT_SHARE_PCT, signal_timeline

    criteria = SignalCriteria(min_cases=min_cases, prr_threshold=prr_threshold, chi2_threshold=chi2_threshold)
    per_year = 4 + (2 if exclude else 0) + (1 if detect_masking else 0)
    with console.status(f"Rebuilding the 2×2 table year by year from openFDA ({per_year} requests per year) …"):
        res = signal_timeline([drug, *alias], reaction, _client(), start_year=start, end_year=end, criteria=criteria,
                              exclude=exclude, detect_masking=detect_masking)

    console.print(Panel.fit(res.headline(), title="Pharos · signal emergence", border_style="red" if res.first_flag_year_cumulative else "green"))

    adj = bool(res.exclude)
    t = Table(box=box.SIMPLE_HEAVY, expand=False, padding=(0, 1))
    t.add_column("Year", justify="right", no_wrap=True)
    t.add_column("Drug×rx /\ndrug reports", justify="right", no_wrap=True)
    t.add_column("Bkgd\n%", justify="right", no_wrap=True)
    t.add_column("PRR\nyear", justify="right", no_wrap=True)
    t.add_column("PRR\ncumul.", justify="right", no_wrap=True)
    if adj:
        t.add_column("Bkgd %\nexcl.", justify="right", no_wrap=True)
        t.add_column("PRR cum.\nexcl.", justify="right", no_wrap=True)
    if detect_masking:
        t.add_column("Top drug in rx\nreports (share)", no_wrap=True)
    t.add_column("Flag", no_wrap=True)
    t.add_column("★", no_wrap=True)
    acts_by_year: dict[int, list[str]] = {}
    for a in res.actions:
        acts_by_year.setdefault(a.year, []).append(a.label)
    for _, r in res.table.iterrows():
        y = int(r["year"])
        flags = []
        if r["cum_signal"]:
            flags.append("● std")
        if adj and r.get("cum_signal_adj"):
            flags.append("◆ excl")
        if r.get("stimulated_reporting"):
            flags.append("📣")
        style = "bold red" if (y in (res.first_flag_year_cumulative, res.first_flag_year_adjusted)) else ("red" if flags else "dim")
        cells = [
            str(y), f"{int(r['a']):,} / {int(r['n_drug']):,}", f"{r['background_pct']:.2f}",
            _fmt(r["prr_year"]) if pd_notna(r["prr_year"]) else "—",
            _fmt(r["cum_prr"]) if pd_notna(r["cum_prr"]) else "—",
        ]
        if adj:
            cells += [f"{r['background_adj_pct']:.2f}", _fmt(r["cum_prr_adj"]) if pd_notna(r.get("cum_prr_adj")) else "—"]
        if detect_masking:
            top = r.get("top_contributor") or ""
            share = r.get("top_contributor_share_pct") or 0.0
            mark = " ⚠" if share >= MASKING_ALERT_SHARE_PCT else ""
            cells.append(f"{top[:14]} ({share:.0f}%){mark}" if top else "—")
        cells += [" ".join(flags), "★" * len(acts_by_year.get(y, []))]
        t.add_row(*cells, style=style)
    console.print(t)
    if adj and res.auto_excluded:
        steps = "; ".join(f"{', '.join(s['names'])} from {s['from_year']}" for s in res.exclusion_schedule)
        console.print(f"[dim]◆ excl = cumulative PRR with maskers removed by rule, prospectively — {steps}. No look-ahead: a product is only "
                      f"excluded from the first year it reached 25% of the reaction's reports.[/dim]")
    elif adj:
        console.print(f"[dim]◆ excl = cumulative PRR with {', '.join(res.exclude)} removed from the comparator background.[/dim]")
    if res.actions:
        console.print("[bold]★ Regulatory / scientific milestones[/bold]")
        for a in res.actions:
            inside = res.start_year <= a.year <= res.end_year
            console.print(f"  {'★' if inside else '·'} {a.date.isoformat()}  {a.label}" + (f"  [dim]({a.source})[/dim]" if a.source else ""),
                          style="" if inside else "dim")
    sy = res.stimulated_years
    if sy:
        fa = res.first_action
        console.print(f"[dim]📣 publicity-stimulated reporting flag: from {sy[0]} onward the reaction's share of this drug's reports is "
                      f"≥ 2× its pre-{fa.year if fa else sy[0]} mean — likely driven by media or litigation, not new risk.[/dim]")
    console.print("[dim]Years = FDA receive date. Cumulative PRR in year Y uses only reports the FDA had by 31 Dec Y. "
                  "Watch the background column: another drug's reporting wave can inflate it and mask this signal.[/dim]")
    if json_out:
        json_out.write_text(json.dumps(res.as_dict(), indent=2, default=str), encoding="utf-8")
        console.print(f"[green]Wrote {json_out}[/green]")


def pd_notna(x) -> bool:
    import pandas as pd

    return x is not None and not (isinstance(x, float) and pd.isna(x))


# ---------------------------------------------------------------- ctd-check


@app.command("ctd-check")
def ctd_check(
    outline: Path = typer.Argument(..., exists=True, readable=True, help="Dossier outline (YAML or JSON)."),
    region: Optional[str] = typer.Option(None, help="US or EU — overrides the outline's own 'region'."),
    report: Optional[Path] = typer.Option(None, help="Write the Markdown gap report here."),
    json_out: Optional[Path] = typer.Option(None, "--json"),
):
    """Check a dossier outline against the ICH M4 CTD structure; score each module; list gaps."""
    from pharos.ctd.checker import check_outline, load_outline
    from pharos.ctd.report import gap_report_markdown

    result = check_outline(load_outline(outline), region=region)

    color = "green" if result.ready_to_submit else "red"
    console.print(
        Panel.fit(
            f"[bold]{result.product}[/bold]  ·  region {result.region}\n"
            f"Overall completeness: [bold {color}]{result.overall_score * 100:.1f}%[/bold {color}]   "
            f"gaps: {len(result.gaps)} ({sum(1 for g in result.gaps if g.severity == 'critical')} critical)\n"
            + ("[bold green]READY TO SUBMIT[/bold green]" if result.ready_to_submit else "[bold red]NOT READY[/bold red]"),
            title="Pharos · CTD readiness",
        )
    )
    mt = Table(box=box.SIMPLE_HEAVY)
    for col in ("Module", "Title", "Score", "Required present", "Draft", "Gaps"):
        mt.add_column(col, justify="right" if col not in ("Module", "Title") else "left")
    for m in result.modules:
        mt.add_row(
            m.module_id,
            m.title,
            f"{m.score * 100:.0f}%",
            f"{m.required_present}/{m.required_total}",
            str(m.required_draft),
            str(len(m.gaps)),
            style="" if m.score >= 1 else ("yellow" if m.score >= 0.8 else "red"),
        )
    console.print(mt)

    if result.gaps:
        gt = Table(title="Gaps — most severe first", box=box.SIMPLE)
        for col in ("Severity", "Section", "Title", "Status", "Why it matters"):
            gt.add_column(col)
        for g in result.gaps:
            gt.add_row(g.severity, g.section_id, g.title, g.status, g.note, style={"critical": "red", "major": "yellow"}.get(g.severity, ""))
        console.print(gt)

    if result.remediation_order:
        gap_by_id = {g.section_id: g for g in result.gaps}
        ot = Table(title="Fix in this order", box=box.SIMPLE_HEAVY)
        for col in ("#", "Section", "Title", "Severity", "Unblocks"):
            ot.add_column(col, justify="right" if col == "#" else "left")
        for i, sid in enumerate(result.remediation_order, 1):
            g = gap_by_id.get(sid)
            if g is None:
                continue
            unblocks = ", ".join(g.blocks) if g.blocks else "—"
            ot.add_row(
                str(i), g.section_id, g.title, g.severity, unblocks,
                style={"critical": "red", "major": "yellow"}.get(g.severity, ""),
            )
        console.print(ot)

    for w in result.warnings:
        console.print(f"[yellow]⚠ {w}[/yellow]")
    for u in result.unmatched_entries:
        console.print(f"[dim]? not a CTD section: {u}[/dim]")

    if report:
        report.write_text(gap_report_markdown(result), encoding="utf-8")
        console.print(f"[green]Wrote {report}[/green]")
    if json_out:
        json_out.write_text(json.dumps(result.as_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]Wrote {json_out}[/green]")
    raise typer.Exit(code=0 if result.ready_to_submit else 1)


# ---------------------------------------------------------------- ctd-template


@app.command("ctd-template")
def ctd_template(
    region: str = typer.Option("US", help="US or EU."),
    status: str = typer.Option("missing", help="Initial status for every section."),
    out: Optional[Path] = typer.Option(None, help="Write YAML here instead of stdout."),
):
    """Emit a blank dossier outline containing every CTD section, for a regulatory team to fill in."""
    import yaml

    from pharos.ctd.checker import outline_template

    text = yaml.safe_dump(outline_template(region, status=status), sort_keys=False, allow_unicode=True)
    if out:
        out.write_text(text, encoding="utf-8")
        console.print(f"[green]Wrote {out}[/green]")
    else:
        sys.stdout.write(text)


# ---------------------------------------------------------------- build-cache


def parse_demo_drugs(path: Path) -> list[dict]:
    """demo_drugs.txt lines: NAME | alias1, alias2 | note.  '#' starts a comment."""
    drugs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        name = parts[0]
        aliases = [a.strip() for a in parts[1].split(",") if a.strip()] if len(parts) > 1 and parts[1] else []
        note = parts[2] if len(parts) > 2 else ""
        drugs.append({"name": name, "aliases": aliases, "note": note})
    return drugs


@app.command("build-cache")
def build_cache(
    drugs_file: Path = typer.Option(DEFAULT_DEMO_DRUGS, help="List of demo drugs to pre-fetch."),
    top: int = typer.Option(50),
):
    """Warm the on-disk openFDA cache for the demo drugs so the demo works offline."""
    from pharos.signals.detector import scan_drug

    client = _client()
    if client.offline:
        console.print("[red]PHAROS_OFFLINE is set — unset it to build the cache.[/red]")
        raise typer.Exit(1)
    drugs = parse_demo_drugs(drugs_file)
    console.print(f"Warming cache in [bold]{client.cache_dir}[/bold] for {len(drugs)} drugs …")
    from pharos.signals.detector import compute_pair

    for d in drugs:
        names = [d["name"], *d["aliases"]]
        with console.status(f"{d['name']} …"):
            res = scan_drug(names, client, top_n=top)
            # The exact 2×2 drill-down (CLI `prr`, dashboard "Drill into one pair") for the signals people will click.
            for rx in list(res.signals()["reaction"].head(8)):
                compute_pair(names, rx, client)
        console.print(f"  ✓ {res.drug:<16} {res.drug_reports:>8,} reports  {len(res.signals()):>3} clinical signals   {d['note']}")

    # Signal-emergence timelines for the headline pairs (4 requests per year each).
    import yaml

    from pharos.signals.timeline import ACTIONS_PATH, signal_timeline

    pairs = (yaml.safe_load(ACTIONS_PATH.read_text(encoding="utf-8")) or {}).get("headline_pairs", [])
    for p in pairs:
        names = [p["drug"], *p.get("aliases", [])]
        # Warm every variant the demo can ask for: standard, the named exclusion, and the automatic rule.
        variants = [None, ["auto"]] + ([p["exclude"]] if p.get("exclude") else [])
        for ex in variants:
            with console.status(f"timeline {p['drug']} × {p['reaction']} ({'standard' if not ex else ', '.join(ex)}) …"):
                tl = signal_timeline(names, p["reaction"], client, end_year=p.get("end_year"), exclude=ex)
        compute_pair(names, p["reaction"], client)  # headline pairs must drill down offline too
        flag = tl.first_flag_year_cumulative or "never"
        console.print(f"  ✓ timeline {tl.drug:<14} × {tl.reaction:<26} standard {flag} · auto-corrected {tl.first_flag_year_adjusted or '—'}")

    # Hidden-signal screens and FDA labels for the demo.
    from pharos.signals.label import load_label
    from pharos.signals.masking import find_hidden_signals

    for h in (yaml.safe_load(ACTIONS_PATH.read_text(encoding="utf-8")) or {}).get("hidden_signal_demos", []):
        names = [h["drug"], *h.get("aliases", [])]
        with console.status(f"hidden signals {h['drug']} as of {h.get('as_of')} …"):
            hs = find_hidden_signals(names, client, as_of_year=h.get("as_of"))
        console.print(f"  ✓ hidden   {hs.drug:<14} as of {hs.end_year}: {len(hs.unmasked)} unmasked, {len(hs.strengthened)} understated")
    for d in drugs:
        with console.status(f"label {d['name']} …"):
            lab = load_label([d["name"], *d["aliases"]], client)
        console.print(f"  ✓ label    {d['name']:<14} {'found: ' + ', '.join(lab.products[:2]) if lab.found else 'no current label'}")
    console.print("[green]Cache ready. Set PHAROS_OFFLINE=1 to run without network.[/green]")


@app.command()
def version():
    console.print(f"pharos {__version__}")


if __name__ == "__main__":
    app()
