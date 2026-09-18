"""Labelledness tests — offline. The label text is a miniature of a real metformin-style label."""

import pandas as pd
import pytest

from pharos.signals.label import (
    LabelInfo,
    _is_single_ingredient,
    _sentences,
    annotate_with_label,
    check_reaction,
    label_summary,
    load_label,
    normalise,
)

SECTIONS = {
    "boxed_warning": "WARNING: LACTIC ACIDOSIS. Postmarketing cases of metformin-associated lactic acidosis have resulted in death. "
                     "Risk factors include renal impairment.",
    "warnings_and_cautions": "Hypoglycemia may occur when used with insulin. Vitamin B12 deficiency has been observed.",
    "adverse_reactions": "The most common adverse reactions are diarrhea, nausea, vomiting and flatulence. Weight loss was reported. "
                         "Increases in blood glucose were reported in some patients. Lactic acidosis is discussed elsewhere.",
}


def make_label(sections=SECTIONS) -> LabelInfo:
    return LabelInfo(
        found=True, names_searched=["TESTDRUG"], n_labels_used=1, products=["Testdrug"],
        sections={fld: [(s, normalise(s)) for s in _sentences(text)] for fld, text in sections.items()},
    )


def test_normalise_maps_british_to_american_spelling():
    assert normalise("HYPOGLYCAEMIA") == "hypoglycemia"
    assert normalise("Diarrhoea / OEDEMA") == "diarrhea edema"
    assert normalise("Gastrointestinal haemorrhage") == "gastrointestinal hemorrhage"


def test_phrase_match_in_boxed_warning_wins_over_lower_sections():
    r = check_reaction("LACTIC ACIDOSIS", make_label())
    assert r["is_labelled"] is True
    assert r["label_section"] == "boxed warning"          # also present in adverse reactions; most prominent wins
    assert r["label_match"] == "phrase"
    assert "lactic acidosis" in r["label_snippet"].lower()


def test_british_spelled_term_matches_american_label():
    r = check_reaction("HYPOGLYCAEMIA", make_label())
    assert r["is_labelled"] and r["label_section"] == "warnings & precautions"
    assert check_reaction("DIARRHOEA", make_label())["label_section"] == "adverse reactions"


def test_synonym_match():
    r = check_reaction("WEIGHT DECREASED", make_label())   # label says "weight loss"
    assert r["is_labelled"] and r["label_match"] == "synonym"


def test_word_order_independent_match_within_one_sentence():
    r = check_reaction("BLOOD GLUCOSE INCREASED", make_label())  # label says "Increases in blood glucose"
    assert r["is_labelled"] and r["label_match"] == "words in one sentence"


def test_words_split_across_sentences_do_not_match():
    lab = make_label({"adverse_reactions": "Glucose was measured. Blood was drawn. Doses were increased."})
    assert check_reaction("BLOOD GLUCOSE INCREASED", lab)["is_labelled"] is False


def test_unlabelled_reaction():
    r = check_reaction("GLOSSODYNIA", make_label())
    assert r["is_labelled"] is False and r["label_status"].startswith("UNLABELLED")


def test_administrative_term_and_missing_label_are_unknown_not_unlabelled():
    assert check_reaction("DRUG INEFFECTIVE", make_label())["is_labelled"] is None
    none = LabelInfo(found=False, names_searched=["WITHDRAWN"])
    r = check_reaction("MYOCARDIAL INFARCTION", none)
    assert r["is_labelled"] is None and r["label_status"] == "no current label"


def test_annotate_and_summary_count_clinical_signals_only():
    table = pd.DataFrame(
        {
            "reaction": ["LACTIC ACIDOSIS", "DIARRHOEA", "GLOSSODYNIA", "DRUG INEFFECTIVE", "NAUSEA"],
            "prr": [80.0, 2.2, 9.0, 3.0, 1.0],
            "is_signal": [True, True, True, True, False],
            "is_administrative": [False, False, False, True, False],
        }
    )
    ann = annotate_with_label(table, make_label())
    assert list(ann["is_labelled"]) == [True, True, False, None, True]
    s = label_summary(ann)
    assert s == {"clinical_signals": 3, "labelled": 2, "unlabelled": 1, "unknown": 0, "boxed_warning": 1,
                 "unlabelled_reactions": ["GLOSSODYNIA"]}


def test_annotate_empty_table_keeps_columns():
    ann = annotate_with_label(pd.DataFrame(columns=["reaction"]), make_label())
    assert "label_status" in ann.columns and ann.empty


@pytest.mark.parametrize(
    "generic,expected",
    [(["METFORMIN HYDROCHLORIDE"], True), (["SITAGLIPTIN AND METFORMIN HYDROCHLORIDE"], False),
     (["AMLODIPINE, VALSARTAN"], False), ([], False)],
)
def test_single_ingredient_detection(generic, expected):
    assert _is_single_ingredient({"generic_name": generic}) is expected


class FakeLabelClient:
    def __init__(self, docs):
        self.docs = docs

    def label_documents(self, names, limit=15):
        return self.docs


def test_load_label_prefers_single_ingredient_prescribing_information():
    combo = {"brand_name": ["ComboPill"], "generic_name": ["OTHERDRUG AND TESTDRUG"], "effective_time": "20250101",
             "sections": {"adverse_reactions": "Glossodynia was common with the other ingredient.", "boxed_warning": "x"}}
    single = {"brand_name": ["Testdrug"], "generic_name": ["TESTDRUG"], "effective_time": "20240601",
              "sections": {"adverse_reactions": "Nausea and diarrhea."}}
    lab = load_label("testdrug", FakeLabelClient([combo, single]))
    assert lab.found and lab.products == ["Testdrug"] and not lab.note
    assert check_reaction("GLOSSODYNIA", lab)["is_labelled"] is False   # the combo label must not leak in


def test_load_label_falls_back_to_combination_with_a_note_and_handles_none():
    combo = {"brand_name": ["ComboPill"], "generic_name": ["OTHERDRUG AND TESTDRUG"], "effective_time": "20250101",
             "sections": {"adverse_reactions": "Nausea."}}
    lab = load_label("testdrug", FakeLabelClient([combo]))
    assert lab.found and "combination" in lab.note.lower()
    assert load_label("withdrawn", FakeLabelClient([])).found is False
