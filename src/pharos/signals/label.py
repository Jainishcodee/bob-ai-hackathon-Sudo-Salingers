"""Labelledness — is this signal already on the FDA-approved label, or is it new?

The first question a pharmacovigilance scientist asks about a statistical signal is "is it
*labelled*?" A disproportionality hit for a reaction that is already in the product's boxed
warning is expected and needs no action; one that appears nowhere on the label is the one worth a
human's time. This module fetches the current US label (SPL) from openFDA's ``/drug/label``
endpoint and classifies each reaction:

    boxed warning  >  warnings & precautions  >  contraindications  >  adverse reactions  >  other
    ... or  UNLABELLED  (not found anywhere in the safety sections)
    ... or  NO LABEL    (no current label in openFDA — typical for withdrawn products)

Matching is text-based and therefore heuristic: MedDRA preferred terms are British-spelled and
formal ("HAEMORRHAGE", "PYREXIA") while labels are American and sometimes lay ("bleeding",
"fever"). We normalise spelling, apply a small synonym table, then fall back to requiring every
significant word of the term inside one sentence. "Unlabelled" therefore means *not found by text
match* — a prompt to read the label, not a regulatory determination. It is reported that way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

from pharos.faers.client import OpenFDAClient
from pharos.signals.detector import ADMINISTRATIVE_TERMS

# Highest regulatory prominence first. (field in openFDA, human label, rank)
SECTION_RANK = [
    ("boxed_warning", "boxed warning"),
    ("warnings_and_cautions", "warnings & precautions"),
    ("warnings", "warnings"),
    ("contraindications", "contraindications"),
    ("precautions", "precautions"),
    ("general_precautions", "precautions"),
    ("adverse_reactions", "adverse reactions"),
    ("use_in_specific_populations", "specific populations"),
    ("drug_interactions", "drug interactions"),
    ("overdosage", "overdosage"),
]

# British (MedDRA) -> American (FDA label) spelling, applied to both sides before matching.
_SPELLING = [
    ("haem", "hem"), ("oedema", "edema"), ("oesophag", "esophag"), ("ischaem", "ischem"),
    ("anaesth", "anesth"), ("paediatric", "pediatric"), ("foetal", "fetal"), ("foetus", "fetus"),
    ("tumour", "tumor"), ("faec", "fec"), ("coeliac", "celiac"), ("leucop", "leukop"),
    ("aemia", "emia"), ("aemic", "emic"), ("rrhoea", "rrhea"), ("pnoea", "pnea"), ("colour", "color"),
    ("gynaec", "gynec"), ("orthopaed", "orthoped"), ("caesar", "cesar"),
]

# MedDRA preferred term -> phrases a label might use instead.
SYNONYMS: dict[str, list[str]] = {
    "MYOCARDIAL INFARCTION": ["heart attack", "myocardial infarct", "myocardial ischemi", "mi)"],
    "ACUTE MYOCARDIAL INFARCTION": ["heart attack", "myocardial infarction"],
    "CEREBROVASCULAR ACCIDENT": ["stroke", "cerebrovascular event"],
    "CARDIAC FAILURE CONGESTIVE": ["congestive heart failure", "heart failure"],
    "CARDIAC FAILURE": ["heart failure"],
    "CARDIAC ARREST": ["cardiac arrest", "cardiorespiratory arrest"],
    "PYREXIA": ["fever"],
    "DYSPNOEA": ["shortness of breath", "dyspnea", "difficulty breathing"],
    "PRURITUS": ["itching", "pruritus"],
    "RENAL FAILURE": ["kidney failure", "renal failure", "renal impairment"],
    "ACUTE KIDNEY INJURY": ["acute renal failure", "kidney injury", "renal failure", "renal impairment", "renal function"],
    "HEPATIC FAILURE": ["liver failure", "hepatic failure"],
    "ALOPECIA": ["hair loss", "alopecia"],
    "HYPERHIDROSIS": ["sweating", "hyperhidrosis"],
    "SOMNOLENCE": ["drowsiness", "somnolence", "sleepiness"],
    "ASTHENIA": ["weakness", "asthenia"],
    "MALAISE": ["malaise", "feeling unwell"],
    "WEIGHT INCREASED": ["weight gain", "increase in weight", "increased weight"],
    "WEIGHT DECREASED": ["weight loss", "decrease in weight", "decreased weight"],
    "DECREASED APPETITE": ["anorexia", "loss of appetite", "decreased appetite"],
    "BLOOD GLUCOSE INCREASED": ["hyperglycemia", "elevated blood glucose", "increased blood glucose"],
    "BLOOD GLUCOSE DECREASED": ["hypoglycemia", "low blood glucose", "low blood sugar"],
    "OEDEMA PERIPHERAL": ["peripheral edema", "edema"],
    "OEDEMA": ["edema", "fluid retention"],
    "FLUID RETENTION": ["fluid retention", "edema"],
    "GASTROINTESTINAL HAEMORRHAGE": ["gastrointestinal bleeding", "gi bleeding", "bleeding, ulceration"],
    "HAEMORRHAGE": ["bleeding", "hemorrhage"],
    "RHABDOMYOLYSIS": ["rhabdomyolysis", "myopathy"],
    "STEVENS-JOHNSON SYNDROME": ["stevens johnson", "sjs"],
    "TOXIC EPIDERMAL NECROLYSIS": ["toxic epidermal necrolysis", "ten)"],
    "ELECTROCARDIOGRAM QT PROLONGED": ["qt prolongation", "prolongation of the qt", "qt interval"],
    "COMPLETED SUICIDE": ["suicide", "suicidal"],
    "SUICIDAL IDEATION": ["suicidal thoughts", "suicidal ideation", "suicidality"],
    "FALL": ["falls", "fall"],
    "VISION BLURRED": ["blurred vision", "vision blurred"],
    "ABDOMINAL PAIN UPPER": ["abdominal pain", "epigastric pain", "stomach pain"],
    "ABDOMINAL DISCOMFORT": ["abdominal discomfort", "abdominal pain", "stomach upset"],
    "DRUG HYPERSENSITIVITY": ["hypersensitivity", "allergic reaction"],
    "HYPERSENSITIVITY": ["hypersensitivity", "allergic reaction"],
    "ANAPHYLACTIC REACTION": ["anaphylaxis", "anaphylactic"],
    "PAIN IN EXTREMITY": ["pain in extremity", "limb pain", "pain in the arms or legs"],
    "LACTIC ACIDOSIS": ["lactic acidosis"],
    "HYPERTENSION": ["hypertension", "high blood pressure", "blood pressure increased"],
    "HYPOTENSION": ["hypotension", "low blood pressure"],
}

_STOP = {"and", "the", "with", "due", "nos", "of", "in", "to"}


def normalise(text: str) -> str:
    s = text.lower()
    for brit, us in _SPELLING:
        s = s.replace(brit, us)
    s = re.sub(r"[^a-z0-9()]+", " ", s)
    return " ".join(s.split())


def _sentences(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.;:•])\s+|\s{2,}", text) if p.strip()]


@dataclass
class LabelInfo:
    found: bool
    names_searched: list[str]
    n_labels_used: int = 0
    products: list[str] = field(default_factory=list)
    generic_names: list[str] = field(default_factory=list)
    effective_time: str | None = None
    sections: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # field -> [(original, normalised)]
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "label_found": self.found,
            "names_searched": self.names_searched,
            "labels_used": self.n_labels_used,
            "products": self.products[:6],
            "generic_names": self.generic_names[:4],
            "most_recent_effective_date": self.effective_time,
            "sections_available": [human for fld, human in SECTION_RANK if fld in self.sections],
            "note": self.note,
        }


def _is_single_ingredient(doc: dict) -> bool:
    gens = doc.get("generic_name") or []
    return bool(gens) and not any(re.search(r"\bAND\b|,|;|\bWITH\b|/", g.upper()) for g in gens)


def load_label(names: str | Iterable[str], client: OpenFDAClient | None = None, max_labels: int = 5) -> LabelInfo:
    """Fetch and index the current label(s). Single-ingredient prescription labels are preferred so a
    combination product's other ingredient does not make a reaction look labelled."""
    if isinstance(names, str):
        names = [names]
    names = [n.strip().upper() for n in names if n and n.strip()]
    client = client or OpenFDAClient()
    docs = client.label_documents(names)
    if not docs:
        return LabelInfo(found=False, names_searched=names,
                         note="No current label in openFDA for these names — typical for withdrawn or discontinued products.")

    single = [d for d in docs if _is_single_ingredient(d)]
    pool = single or docs
    # Prefer full prescribing information (has an adverse-reactions section), longest first.
    pool.sort(key=lambda d: ("adverse_reactions" in d["sections"], sum(len(v) for v in d["sections"].values())), reverse=True)
    chosen = pool[:max_labels]

    sections: dict[str, list[tuple[str, str]]] = {}
    for d in chosen:
        for fld, text in d["sections"].items():
            sections.setdefault(fld, []).extend((s, normalise(s)) for s in _sentences(text))
    note = "" if single else "Only combination-product labels were available; a reaction may be labelled because of the other ingredient."
    return LabelInfo(
        found=True, names_searched=names, n_labels_used=len(chosen),
        products=sorted({b for d in chosen for b in d.get("brand_name", [])}),
        generic_names=sorted({g for d in chosen for g in d.get("generic_name", [])}),
        effective_time=max((d.get("effective_time") or "" for d in chosen), default=None) or None,
        sections=sections, note=note,
    )


def _token_match(tokens: list[str], sentence_norm: str) -> bool:
    words = sentence_norm.split()
    for t in tokens:
        stem = t[:5] if len(t) >= 6 else t
        if not any(w.startswith(stem) if len(t) >= 6 else w == t for w in words):
            return False
    return True


def check_reaction(term: str, label: LabelInfo) -> dict:
    """Where (if anywhere) does this MedDRA term appear on the label?"""
    t = term.strip().upper()
    if t in ADMINISTRATIVE_TERMS:
        return {"label_status": "n/a (administrative term)", "is_labelled": None, "label_section": "", "label_snippet": "", "label_match": ""}
    if not label.found:
        return {"label_status": "no current label", "is_labelled": None, "label_section": "", "label_snippet": "", "label_match": ""}

    phrase = normalise(t)
    phrases = [phrase] + [normalise(s) for s in SYNONYMS.get(t, [])]
    tokens = [w for w in phrase.split() if len(w) > 2 and w not in _STOP]

    for fld, human in SECTION_RANK:
        for original, norm in label.sections.get(fld, []):
            hit = next((p for p in phrases if p and p in norm), None)
            method = "phrase" if hit == phrase else ("synonym" if hit else "")
            if not hit and len(tokens) >= 2 and _token_match(tokens, norm):
                hit, method = " + ".join(tokens), "words in one sentence"
            if hit:
                snippet = original if len(original) <= 220 else original[:217] + "…"
                return {"label_status": f"labelled — {human}", "is_labelled": True, "label_section": human,
                        "label_snippet": snippet, "label_match": method}
    return {"label_status": "UNLABELLED (not found on label)", "is_labelled": False, "label_section": "",
            "label_snippet": "", "label_match": ""}


LABEL_COLUMNS = ["label_status", "is_labelled", "label_section", "label_snippet", "label_match"]


def annotate_with_label(table: pd.DataFrame, label: LabelInfo, reaction_col: str = "reaction") -> pd.DataFrame:
    """Add label columns to any table that has a reaction column."""
    if table is None or table.empty:
        out = table.copy() if table is not None else pd.DataFrame()
        for c in LABEL_COLUMNS:
            out[c] = []
        return out
    checks = [check_reaction(r, label) for r in table[reaction_col]]
    return pd.concat([table.reset_index(drop=True), pd.DataFrame(checks, columns=LABEL_COLUMNS)], axis=1)


def label_summary(annotated: pd.DataFrame) -> dict:
    """Counts over CLINICAL SIGNALS only — the numbers a reviewer wants first."""
    if annotated is None or annotated.empty or "is_labelled" not in annotated:
        return {"clinical_signals": 0, "labelled": 0, "unlabelled": 0, "unknown": 0, "unlabelled_reactions": []}
    sig = annotated[annotated["is_signal"].astype(bool) & ~annotated["is_administrative"].astype(bool)]
    labelled = sig[sig["is_labelled"] == True]  # noqa: E712 — column holds True/False/None
    unlabelled = sig[sig["is_labelled"] == False]  # noqa: E712
    return {
        "clinical_signals": int(len(sig)),
        "labelled": int(len(labelled)),
        "unlabelled": int(len(unlabelled)),
        "unknown": int(len(sig) - len(labelled) - len(unlabelled)),
        "boxed_warning": int((sig["label_section"] == "boxed warning").sum()),
        "unlabelled_reactions": list(unlabelled.sort_values("prr", ascending=False)["reaction"]) if "prr" in unlabelled else list(unlabelled["reaction"]),
    }
