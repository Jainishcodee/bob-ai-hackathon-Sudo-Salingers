"""Pharos dashboard — two tabs: Signal Detection and Submission Readiness.

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml
from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))

from pharos import __version__  # noqa: E402
from pharos.cli import parse_demo_drugs  # noqa: E402
from pharos.ctd.checker import check_outline, load_outline  # noqa: E402
from pharos.ctd.report import gap_report_markdown  # noqa: E402
from pharos.faers.client import OpenFDAClient, OpenFDAError  # noqa: E402
from pharos.signals.cluster import cluster_signals  # noqa: E402
from pharos.signals.detector import compute_pair, scan_drug  # noqa: E402
from pharos.signals.stats import SignalCriteria  # noqa: E402
from pharos.signals.timeline import actions_for, signal_timeline  # noqa: E402

load_dotenv()

SAMPLES = SRC_DIR / "data" / "samples"
TIER_COLOR = {"strong": "#C0392B", "moderate": "#E67E22", "weak": "#F1C40F", "none": "#95A5A6"}
SEV_COLOR = {"critical": "#C0392B", "major": "#E67E22", "minor": "#F1C40F"}

st.set_page_config(page_title="Pharos — drug safety", page_icon="🔦", layout="wide")


# ------------------------------------------------------------------ cached workers


@st.cache_resource
def get_client() -> OpenFDAClient:
    return OpenFDAClient()


@st.cache_data(show_spinner=False, ttl=3600)
def cached_scan(names: tuple[str, ...], top_n: int, min_cases: int, prr_t: float, chi2_t: float) -> dict:
    res = scan_drug(list(names), get_client(), top_n=top_n, criteria=SignalCriteria(min_cases, prr_t, chi2_t))
    return {
        "meta": res.as_dict(top=0) | {"rows": None},
        "table": res.table.to_json(orient="split"),
        "source": res.source,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def cached_pair(names: tuple[str, ...], reaction: str) -> dict:
    return compute_pair(list(names), reaction, get_client())


@st.cache_data(show_spinner=False, ttl=3600)
def cached_timeline(names: tuple[str, ...], reaction: str, start: int, end: int, min_cases: int, prr_t: float, chi2_t: float,
                    exclude: tuple[str, ...] = ()) -> dict:
    res = signal_timeline(list(names), reaction, get_client(), start_year=start, end_year=end,
                          criteria=SignalCriteria(min_cases, prr_t, chi2_t), exclude=list(exclude) or None)
    return res.as_dict()


def demo_drugs() -> list[dict]:
    return parse_demo_drugs(SAMPLES / "demo_drugs.txt")


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.markdown("## 🔦 Pharos")
    st.caption(f"v{__version__} · *a lighthouse for drug safety*")
    client = get_client()
    mode = "🔌 offline (cache only)" if client.offline else ("🔑 live · keyed" if client.api_key else "🌐 live · keyless")
    st.markdown(f"**Data source:** openFDA FAERS — {mode}")
    try:
        st.metric("Reports in FAERS (openFDA)", f"{client.total_reports():,}")
    except OpenFDAError as exc:
        st.error(str(exc))
    st.divider()
    st.markdown(
        "**How IBM Bob fits**\n\n"
        "Pharos is the *evidence layer*: it returns numbers, tables and structured gaps. "
        "IBM Bob, connected through the Pharos **MCP server**, is the *reasoning layer* that reads "
        "that evidence and writes the signal assessment or the dossier remediation memo.\n\n"
        "Each tab shows the prompt to paste into Bob."
    )
    st.caption("See `docs/bob-integration.md`.")

st.title("🔦 Pharos")
st.markdown(
    "**Mode 1 · Signal Detection** — disproportionality analysis (PRR / ROR / χ²) over 20M+ real FDA adverse-event reports.  \n"
    "**Mode 2 · Submission Readiness** — audit a drug-approval dossier outline against the ICH M4 Common Technical Document."
)

tab1, tab2 = st.tabs(["🚨 Signal Detection (FAERS)", "📋 Submission Readiness (ICH M4 CTD)"])

# ================================================================== TAB 1

with tab1:
    left, right = st.columns([2, 1])
    with left:
        demos = demo_drugs()
        labels = ["— type a drug —"] + [f"{d['name']}  ·  {d['note']}" for d in demos]
        pick = st.selectbox("Demo drugs (all withdrawn/restricted for reasons visible in FAERS)", labels, index=1)
        chosen = demos[labels.index(pick) - 1] if pick != labels[0] else None
        c1, c2 = st.columns(2)
        drug = c1.text_input("Drug name (as reported to FAERS)", value=chosen["name"] if chosen else "")
        aliases = c2.text_input("Aliases / brand names (comma-separated)", value=", ".join(chosen["aliases"]) if chosen else "")
    with right:
        st.markdown("**Signal criteria** (defaults = Evans 2001)")
        top_n = st.slider("Reactions to evaluate", 10, 200, 50, 10)
        min_cases = st.number_input("Min cases (a)", 1, 50, 3)
        prr_t = st.number_input("PRR ≥", 1.0, 10.0, 2.0, 0.5)
        chi2_t = st.number_input("χ² ≥", 0.0, 50.0, 4.0, 1.0)

    run = st.button("🔍 Scan for signals", type="primary", disabled=not drug.strip())

    if run or ("scan_names" in st.session_state and st.session_state.get("scan_names") == (drug, aliases)):
        names = tuple(n.strip() for n in [drug, *aliases.split(",")] if n.strip())
        st.session_state["scan_names"] = (drug, aliases)
        try:
            with st.spinner(f"Querying openFDA for {', '.join(n.upper() for n in names)} …"):
                out = cached_scan(names, top_n, int(min_cases), float(prr_t), float(chi2_t))
        except OpenFDAError as exc:
            st.error(f"openFDA error: {exc}")
            st.stop()

        meta = out["meta"]
        df = pd.read_json(io.StringIO(out["table"]), orient="split")
        clinical = df[df["is_signal"] & ~df["is_administrative"]].reset_index(drop=True)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Reports mentioning drug", f"{meta['reports_mentioning_drug']:,}")
        m2.metric("Reactions evaluated", f"{meta['n_reactions_evaluated']}")
        m3.metric("Clinical signals", f"{len(clinical)}", help="Meets criteria and is not an administrative term")
        if not clinical.empty:
            m4.metric("Strongest signal", clinical.iloc[0]["reaction"].title(), f"PRR {clinical.iloc[0]['prr']:.1f}")
            m5.metric("Largest signal (cases)", clinical.sort_values("n_cases", ascending=False).iloc[0]["reaction"].title(),
                      f"n = {int(clinical['n_cases'].max()):,}")
        st.caption(f"Source: openFDA ({out['source']}) · generated {meta['generated_at']} · {meta['total_reports_in_faers']:,} reports in FAERS")

        if chosen and chosen["name"].upper() == names[0].upper():
            st.info(f"**Known history:** {chosen['note']}. Does the statistics find it?", icon="📖")

        if clinical.empty:
            st.warning("No clinical signals under these criteria.")
        else:
            g1, g2 = st.columns([3, 2])
            with g1:
                top = clinical.head(25).iloc[::-1]
                fig = go.Figure(
                    go.Bar(
                        x=top["prr"],
                        y=top["reaction"].str.title(),
                        orientation="h",
                        marker_color=[TIER_COLOR[t] for t in top["tier"]],
                        error_x=dict(type="data", symmetric=False, array=top["prr_ci_high"] - top["prr"], arrayminus=top["prr"] - top["prr_ci_low"], thickness=1),
                        customdata=top[["n_cases", "chi2", "ror", "tier"]].values,
                        hovertemplate="<b>%{y}</b><br>PRR %{x:.2f}<br>n = %{customdata[0]:,}<br>χ² %{customdata[1]:,.0f}<br>ROR %{customdata[2]:.2f}<br>tier %{customdata[3]}<extra></extra>",
                    )
                )
                fig.add_vline(x=prr_t, line_dash="dash", line_color="#7F8C8D", annotation_text=f"PRR = {prr_t}")
                fig.update_layout(
                    title="Clinical signals — PRR with 95% CI (log scale)",
                    xaxis_type="log", xaxis_title="Proportional Reporting Ratio", yaxis_title="",
                    height=max(400, 22 * len(top) + 120), margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig, width="stretch")
            with g2:
                cl = cluster_signals(df)
                if not cl.empty:
                    fig2 = go.Figure(
                        go.Bar(
                            x=cl["n_cases"], y=cl["soc"], orientation="h", marker_color="#2C3E50",
                            customdata=cl[["n_reactions", "max_prr", "strongest_reaction"]].values,
                            hovertemplate="<b>%{y}</b><br>cases %{x:,}<br>signals %{customdata[0]}<br>max PRR %{customdata[1]:.1f}<br>strongest: %{customdata[2]}<extra></extra>",
                        )
                    )
                    fig2.update_layout(title="Signals by organ system (cases)", yaxis=dict(autorange="reversed"), xaxis_title="cases",
                                       height=max(400, 28 * len(cl) + 120), margin=dict(l=10, r=10, t=50, b=10))
                    st.plotly_chart(fig2, width="stretch")
                    st.caption("Heuristic MedDRA SOC mapping — confirm against licensed MedDRA.")

        st.markdown("#### All evaluated reactions")
        show_all = st.toggle("Include non-signals and administrative terms", value=False)
        view = df if show_all else clinical
        pretty = view.assign(
            **{
                "PRR [95% CI]": view.apply(lambda r: f"{r.prr:.2f} [{r.prr_ci_low:.2f}–{r.prr_ci_high:.2f}]", axis=1),
                "ROR": view["ror"].round(2),
                "χ²": view["chi2"].round(1),
            }
        )[["reaction", "n_cases", "PRR [95% CI]", "ROR", "χ²", "tier", "is_signal", "is_administrative"]]
        st.dataframe(pretty, width="stretch", hide_index=True, height=min(600, 38 * len(pretty) + 40))

        d1, d2 = st.columns(2)
        d1.download_button("⬇ CSV", df.to_csv(index=False).encode(), file_name=f"pharos_{names[0]}_scan.csv", mime="text/csv")
        d2.download_button("⬇ JSON", json.dumps(meta | {"rows": df.to_dict(orient='records')}, indent=2, default=str).encode(),
                           file_name=f"pharos_{names[0]}_scan.json", mime="application/json")

        with st.expander("🔬 Drill into one drug–reaction pair (exact 2×2 query)"):
            options = list(df["reaction"])
            rx = st.selectbox("Reaction", options, index=0)
            if st.button("Compute exact 2×2"):
                with st.spinner("Querying …"):
                    pair = cached_pair(names, rx)
                tb = pair["table"]
                grid = pd.DataFrame(
                    {rx.title(): [f"a = {int(tb['a']):,}", f"c = {int(tb['c']):,}"], "Other reactions": [f"b = {int(tb['b']):,}", f"d = {int(tb['d']):,}"]},
                    index=[pair["drug"].title(), "Other drugs"],
                )
                st.table(grid)
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("PRR", f"{pair['prr']:.2f}", f"CI {pair['prr_ci_low']:.2f}–{pair['prr_ci_high']:.2f}", delta_color="off")
                k2.metric("ROR", f"{pair['ror']:.2f}", f"CI {pair['ror_ci_low']:.2f}–{pair['ror_ci_high']:.2f}", delta_color="off")
                k3.metric("χ² (Yates)", f"{pair['chi2']:,.1f}")
                k4.metric("Verdict", "SIGNAL" if pair["is_signal"] else "no signal", pair["tier"], delta_color="inverse" if pair["is_signal"] else "off")

        with st.expander("📈 When did this signal emerge? — year-by-year PRR vs. real regulatory action dates", expanded=True):
            st.markdown(
                "Rebuilds the 2×2 table for each year using FDA **receive date**, so the *cumulative* line shows what a safety "
                "scientist running this screen **in that year** would have seen. The first year it crosses the threshold is the "
                "first-flag year; the dashed markers are real regulatory milestones."
            )
            t1, t2, t3, t4 = st.columns([2, 2, 1, 1])
            default_rx = "MYOCARDIAL INFARCTION" if "MYOCARDIAL INFARCTION" in list(df["reaction"]) else (clinical.iloc[0]["reaction"] if not clinical.empty else df.iloc[0]["reaction"])
            tl_rx = t1.selectbox("Reaction", list(df["reaction"]), index=list(df["reaction"]).index(default_rx), key="tl_rx")
            is_avandia = names[0].upper() == "ROSIGLITAZONE"
            tl_excl = t2.text_input("Exclude from background (masking correction)", value="ROFECOXIB, VIOXX" if is_avandia else "", key="tl_excl",
                                    help="Another drug's reporting wave can dominate a reaction's reports and hide this drug's signal. Name it here to remove it from the comparator.")
            tl_from = t3.number_input("From", 2004, 2030, 2004, key="tl_from")
            tl_to = t4.number_input("To", 2004, 2030, 2013 if is_avandia else 2015, key="tl_to")
            if st.button("📈 Build timeline", key="tl_btn", help="4–7 openFDA requests per year; cached afterwards"):
                excl = tuple(e.strip() for e in tl_excl.split(",") if e.strip())
                try:
                    with st.spinner("Rebuilding the 2×2 table year by year …"):
                        tl = cached_timeline(names, tl_rx, int(tl_from), int(tl_to), int(min_cases), float(prr_t), float(chi2_t), excl)
                except OpenFDAError as exc:
                    st.error(f"openFDA error: {exc}")
                    tl = None
                if tl and tl["rows"]:
                    tdf = pd.DataFrame(tl["rows"])
                    first = tl["first_flag_year_cumulative"]
                    first_adj = tl.get("first_flag_year_masking_corrected")
                    acts = tl["regulatory_actions"]
                    has_adj = bool(tl.get("excluded_from_background"))
                    cols = st.columns(4 if has_adj else 3)
                    cols[0].metric("First flagged — standard", str(first) if first else "never", help="First year the cumulative 2×2 met the criteria")
                    if has_adj:
                        gained = (first - first_adj) if (first and first_adj) else None
                        cols[1].metric("First flagged — masking-corrected", str(first_adj) if first_adj else "never",
                                       f"{gained} yr earlier" if gained and gained > 0 else None, delta_color="inverse")
                    if acts:
                        cols[-2].metric("First regulatory action", str(acts[0]["year"]), acts[0]["label"][:60], delta_color="off")
                        lt = tl["lead_time_years_vs_first_action_masking_corrected"] if has_adj else tl["lead_time_years_vs_first_action"]
                        if lt is not None:
                            cols[-1].metric("Lead time" + (" (corrected)" if has_adj else ""), f"{lt:+d} yr",
                                            "flagged BEFORE regulators acted" if lt > 0 else ("same year" if lt == 0 else "flagged AFTER regulators acted"),
                                            delta_color="normal" if lt > 0 else "inverse")
                    st.info(tl["headline"], icon="🕰️")
                    mm = tl.get("worst_masking_year")
                    if mm and mm["share_pct"] >= 25:
                        st.warning(f"**Masking detected.** In {mm['year']}, **{mm['drug']}** accounted for **{mm['share_pct']:.0f}%** of all "
                                   f"{tl['reaction'].title()} reports in FAERS — inflating the background {tl['drug'].title()} is compared against."
                                   + ("" if has_adj else f" Add `{mm['drug']}` to *Exclude from background* and rebuild to correct for it."), icon="🎭")

                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=tdf["year"], y=tdf["cum_prr"], mode="lines+markers", name="Cumulative PRR — standard (what was knowable that year)",
                                              line=dict(color="#C0392B", width=3),
                                              customdata=tdf[["cum_a", "cum_chi2", "cum_prr_ci_low", "cum_prr_ci_high"]].values,
                                              hovertemplate="<b>%{x}</b><br>cumulative PRR %{y:.2f} [%{customdata[2]:.2f}–%{customdata[3]:.2f}]<br>cumulative cases %{customdata[0]:,}<br>χ² %{customdata[1]:,.0f}<extra></extra>"))
                    if has_adj and "cum_prr_adj" in tdf:
                        fig3.add_trace(go.Scatter(x=tdf["year"], y=tdf["cum_prr_adj"], mode="lines+markers",
                                                  name=f"Cumulative PRR — excluding {', '.join(tl['excluded_from_background']).title()}",
                                                  line=dict(color="#27AE60", width=3),
                                                  customdata=tdf[["background_adj_pct", "excluded_share_of_event_pct"]].values,
                                                  hovertemplate="<b>%{x}</b><br>corrected PRR %{y:.2f}<br>corrected background %{customdata[0]:.2f}%<br>excluded drug's share of reaction reports %{customdata[1]:.0f}%<extra></extra>"))
                    fig3.add_trace(go.Scatter(x=tdf["year"], y=tdf["prr_year"], mode="lines+markers", name="PRR that year only",
                                              line=dict(color="#7F8C8D", width=1.5, dash="dot"),
                                              customdata=tdf[["a", "n_drug"]].values,
                                              hovertemplate="<b>%{x}</b><br>yearly PRR %{y:.2f}<br>cases %{customdata[0]:,} of %{customdata[1]:,} drug reports<extra></extra>"))
                    fig3.add_hline(y=prr_t, line_dash="dash", line_color="#2C3E50", annotation_text=f"signal threshold PRR = {prr_t}", annotation_position="bottom right")
                    if first:
                        fig3.add_vline(x=first, line_color="#C0392B", line_width=2, annotation_text=f"standard: {first}", annotation_position="top left")
                    if has_adj and first_adj:
                        fig3.add_vline(x=first_adj - 0.03, line_color="#27AE60", line_width=2, annotation_text=f"corrected: {first_adj}", annotation_position="bottom left")
                    for a in acts:
                        if int(tl_from) <= a["year"] <= int(tl_to):
                            fig3.add_vline(x=a["year"] + 0.02, line_dash="dash", line_color="#0f62fe")
                            fig3.add_annotation(x=a["year"], y=1, yref="paper", text=a["label"][:48] + ("…" if len(a["label"]) > 48 else ""),
                                                showarrow=False, textangle=-90, xanchor="right", yanchor="top", font=dict(size=10, color="#0f62fe"))
                    fig3.update_layout(title=f"{tl['drug']} × {tl['reaction'].title()} — signal emergence", yaxis_type="log", yaxis_title="PRR (log)",
                                       xaxis=dict(dtick=1, title="year (FDA receive date)"), height=460, legend=dict(orientation="h", y=-0.2),
                                       margin=dict(l=10, r=10, t=60, b=10))
                    st.plotly_chart(fig3, width="stretch")
                    with st.expander("Year-by-year table"):
                        show_cols = ["year", "n_drug", "a", "share_of_drug_reports_pct", "background_pct", "prr_year", "cum_a", "cum_prr", "cum_chi2", "cum_signal"]
                        renames = {"n_drug": "drug reports", "a": "drug × reaction", "share_of_drug_reports_pct": "% of drug reports",
                                   "background_pct": "background %", "prr_year": "PRR (year)", "cum_a": "cum. cases", "cum_prr": "PRR (cum.)",
                                   "cum_chi2": "χ² (cum.)", "cum_signal": "signal"}
                        if has_adj:
                            show_cols += ["background_adj_pct", "cum_prr_adj", "cum_signal_adj"]
                            renames.update({"background_adj_pct": "background % (excl.)", "cum_prr_adj": "PRR cum. (excl.)", "cum_signal_adj": "signal (excl.)"})
                        if "top_contributor" in tdf:
                            show_cols += ["top_contributor", "top_contributor_share_pct"]
                            renames.update({"top_contributor": "top drug in reaction's reports", "top_contributor_share_pct": "its share %"})
                        st.dataframe(tdf[show_cols].rename(columns=renames).round(2), width="stretch", hide_index=True)
                    st.caption("Late spikes usually reflect publicity- or litigation-stimulated reporting rather than new risk — a known bias Bob is instructed to name. "
                               "The 'top drug' column shows who dominates the reaction's reports each year: that is the masking check.")

        with st.expander("🤖 Ask IBM Bob to write the signal assessment", expanded=True):
            st.markdown(
                "With the Pharos MCP server registered in Bob, paste this prompt. Bob calls `scan_signals`, `compute_prr`, "
                "`search_reports` and `signal_emergence_timeline` itself, then writes the memo:"
            )
            st.code(
                f"Using the pharos tools, run a signal assessment for {names[0]}"
                + (f" (aliases: {', '.join(names[1:])})" if len(names) > 1 else "")
                + ". Confirm the top 3 clinical signals with compute_prr, pull 2 real cases each with search_reports, "
                "group by organ system, and for the strongest signal run signal_emergence_timeline to establish when it first met "
                "the criteria and the lead time versus any regulatory action. Write a BLUF-style memo. State n, PRR with CI and "
                "chi-square for each signal, name likely reporting biases, and recommend a next step. Do not claim causation.",
                language="text",
            )

    st.divider()
    st.caption(
        "**Interpretation.** PRR/ROR measure disproportionality of *reporting*, not incidence or causation. Administrative terms "
        "(e.g. DRUG INEFFECTIVE) are computed but excluded from clinical signals. Litigation and media coverage inflate reporting for "
        "specific pairs (notoriety bias) — Vioxx numbers are a textbook example. openFDA data begins in 2004."
    )

# ================================================================== TAB 2

with tab2:
    s1, s2 = st.columns([2, 1])
    with s1:
        source = st.radio("Dossier outline", ["Sample — incomplete dossier", "Sample — complete dossier", "Upload my own (YAML / JSON)"], horizontal=True)
        uploaded = None
        if source.startswith("Upload"):
            uploaded = st.file_uploader("Outline file", type=["yaml", "yml", "json"])
    with s2:
        region = st.selectbox("Region (Module 1 variant)", ["from outline", "US", "EU"])

    outline = None
    if source.startswith("Sample — incomplete"):
        outline = load_outline(SAMPLES / "dossier_incomplete.yaml")
    elif source.startswith("Sample — complete"):
        outline = load_outline(SAMPLES / "dossier_complete.yaml")
    elif uploaded is not None:
        text = uploaded.read().decode("utf-8")
        outline = json.loads(text) if uploaded.name.endswith(".json") else yaml.safe_load(text)

    if outline is not None:
        result = check_outline(outline, region=None if region == "from outline" else region)
        crit = sum(1 for g in result.gaps if g.severity == "critical")

        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Overall completeness", f"{result.overall_score * 100:.1f}%")
        h2.metric("Verdict", "READY" if result.ready_to_submit else "NOT READY", f"{len(result.gaps)} gaps", delta_color="off" if result.ready_to_submit else "inverse")
        h3.metric("Critical gaps", crit, help="Rejection-grade if missing")
        h4.metric("Sections matched", result.matched_sections)
        st.caption(f"**{result.product}** · region {result.region} · {result.spec_version}")

        mod_df = pd.DataFrame([m.as_dict() for m in result.modules])
        fig = go.Figure(
            go.Bar(
                x=mod_df["score_pct"], y=[f"M{m} · {t}" for m, t in zip(mod_df["module_id"], mod_df["title"])], orientation="h",
                marker_color=["#27AE60" if s >= 100 else ("#E67E22" if s >= 80 else "#C0392B") for s in mod_df["score_pct"]],
                text=[f"{s:.0f}%" for s in mod_df["score_pct"]], textposition="outside",
                customdata=mod_df[["required_present", "required_total", "required_draft"]].values,
                hovertemplate="<b>%{y}</b><br>%{x:.0f}% complete<br>required present %{customdata[0]}/%{customdata[1]}<br>draft %{customdata[2]}<extra></extra>",
            )
        )
        fig.update_layout(title="Completeness by CTD module (weighted, required sections)", xaxis=dict(range=[0, 110], title="%"),
                          yaxis=dict(autorange="reversed"), height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, width="stretch")

        st.markdown("#### Gaps in required sections — most severe first")
        if result.gaps:
            gap_df = pd.DataFrame([g.as_dict() for g in result.gaps])[["severity", "section_id", "title", "module", "status", "note"]]
            st.dataframe(
                gap_df.style.map(lambda v: f"color: {SEV_COLOR.get(v, 'inherit')}; font-weight: 700", subset=["severity"]),
                width="stretch", hide_index=True,
            )
        else:
            st.success("No gaps in required sections.")

        w1, w2 = st.columns(2)
        with w1:
            if result.warnings:
                st.markdown("#### ⚠️ Warnings")
                for w in result.warnings:
                    st.warning(w)
        with w2:
            if result.unmatched_entries:
                st.markdown("#### ❔ Not recognised as CTD sections")
                for u in result.unmatched_entries:
                    st.info(u)
            optional = [(m.module_id, o) for m in result.modules for o in m.optional_missing]
            if optional:
                with st.expander(f"Optional / conditional sections not present ({len(optional)})"):
                    for mid, o in optional:
                        st.markdown(f"- Module {mid}: {o}")

        md = gap_report_markdown(result)
        st.download_button("⬇ Markdown gap report", md.encode("utf-8"), file_name="pharos_ctd_gap_report.md", mime="text/markdown")
        st.download_button("⬇ JSON", json.dumps(result.as_dict(), indent=2).encode(), file_name="pharos_ctd_check.json", mime="application/json")

        with st.expander("🤖 Ask IBM Bob to write the remediation memo", expanded=True):
            path_hint = "data/samples/dossier_incomplete.yaml" if source.startswith("Sample — incomplete") else ("data/samples/dossier_complete.yaml" if source.startswith("Sample — complete") else "<path to your outline>")
            st.code(
                f"Using the pharos tools, call check_ctd_dossier on {path_hint}. Write a memo for the regulatory affairs lead: "
                "readiness verdict, module-by-module status, critical gaps first with why each would trigger a refuse-to-file or "
                "major deficiency, a remediation order that respects dependencies (e.g. 2.7 depends on 5.3.5.3), and the owning team for each gap.",
                language="text",
            )

        with st.expander("View raw outline"):
            st.code(yaml.safe_dump(outline, sort_keys=False, allow_unicode=True), language="yaml")
    else:
        st.info("Choose a sample or upload an outline. Need a blank one? Run `python -m pharos ctd-template --out my_dossier.yaml`.")

    st.divider()
    st.caption(
        "Checklist encodes ICH M4(R4) Modules 1–5 (69 leaf sections; Module 1 simplified per region). Severity: critical = rejection-grade "
        "if missing, major = deficiency letter, minor = administrative. Confirm against current agency guidance before use."
    )
