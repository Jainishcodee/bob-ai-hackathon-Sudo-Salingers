"""Group flagged reactions into clinically meaningful clusters.

MedDRA organises reaction terms into 27 System Organ Classes (SOCs). The MedDRA
hierarchy itself is licensed by the MSSO and is NOT bundled here. Instead we ship a
curated map of the most common FAERS preferred terms to their SOC, backed by keyword
heuristics for anything unmapped. Assignments are therefore *approximate* and are
labelled ``heuristic`` in the output so a reviewer knows to confirm them.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------- curated PT -> SOC
PT_TO_SOC: dict[str, str] = {
    # Cardiac
    "MYOCARDIAL INFARCTION": "Cardiac disorders",
    "ACUTE MYOCARDIAL INFARCTION": "Cardiac disorders",
    "CARDIAC ARREST": "Cardiac disorders",
    "CARDIAC FAILURE": "Cardiac disorders",
    "CARDIAC FAILURE CONGESTIVE": "Cardiac disorders",
    "ATRIAL FIBRILLATION": "Cardiac disorders",
    "TACHYCARDIA": "Cardiac disorders",
    "BRADYCARDIA": "Cardiac disorders",
    "PALPITATIONS": "Cardiac disorders",
    "ANGINA PECTORIS": "Cardiac disorders",
    "ARRHYTHMIA": "Cardiac disorders",
    "CARDIAC DISORDER": "Cardiac disorders",
    "CORONARY ARTERY DISEASE": "Cardiac disorders",
    "CORONARY ARTERY OCCLUSION": "Cardiac disorders",
    "MYOCARDIAL ISCHAEMIA": "Cardiac disorders",
    "VENTRICULAR TACHYCARDIA": "Cardiac disorders",
    "ELECTROCARDIOGRAM QT PROLONGED": "Investigations",
    "TORSADE DE POINTES": "Cardiac disorders",
    "SUDDEN CARDIAC DEATH": "Cardiac disorders",
    "CARDIO-RESPIRATORY ARREST": "Cardiac disorders",
    # Vascular
    "HYPERTENSION": "Vascular disorders",
    "HYPOTENSION": "Vascular disorders",
    "DEEP VEIN THROMBOSIS": "Vascular disorders",
    "THROMBOSIS": "Vascular disorders",
    "EMBOLISM": "Vascular disorders",
    "HAEMORRHAGE": "Vascular disorders",
    "FLUSHING": "Vascular disorders",
    "HOT FLUSH": "Vascular disorders",
    "SHOCK": "Vascular disorders",
    "CIRCULATORY COLLAPSE": "Vascular disorders",
    # Nervous system
    "CEREBROVASCULAR ACCIDENT": "Nervous system disorders",
    "STROKE": "Nervous system disorders",
    "ISCHAEMIC STROKE": "Nervous system disorders",
    "TRANSIENT ISCHAEMIC ATTACK": "Nervous system disorders",
    "HEADACHE": "Nervous system disorders",
    "DIZZINESS": "Nervous system disorders",
    "SEIZURE": "Nervous system disorders",
    "CONVULSION": "Nervous system disorders",
    "SOMNOLENCE": "Nervous system disorders",
    "TREMOR": "Nervous system disorders",
    "SYNCOPE": "Nervous system disorders",
    "LOSS OF CONSCIOUSNESS": "Nervous system disorders",
    "PARAESTHESIA": "Nervous system disorders",
    "HYPOAESTHESIA": "Nervous system disorders",
    "MEMORY IMPAIRMENT": "Nervous system disorders",
    "NEUROPATHY PERIPHERAL": "Nervous system disorders",
    "MIGRAINE": "Nervous system disorders",
    "DYSGEUSIA": "Nervous system disorders",
    "BALANCE DISORDER": "Nervous system disorders",
    "DEMENTIA": "Nervous system disorders",
    "AMNESIA": "Nervous system disorders",
    "TARDIVE DYSKINESIA": "Nervous system disorders",
    "EXTRAPYRAMIDAL DISORDER": "Nervous system disorders",
    # Psychiatric
    "DEPRESSION": "Psychiatric disorders",
    "ANXIETY": "Psychiatric disorders",
    "INSOMNIA": "Psychiatric disorders",
    "SUICIDAL IDEATION": "Psychiatric disorders",
    "COMPLETED SUICIDE": "Psychiatric disorders",
    "SUICIDE ATTEMPT": "Psychiatric disorders",
    "CONFUSIONAL STATE": "Psychiatric disorders",
    "HALLUCINATION": "Psychiatric disorders",
    "AGITATION": "Psychiatric disorders",
    "ABNORMAL DREAMS": "Psychiatric disorders",
    "NERVOUSNESS": "Psychiatric disorders",
    "IRRITABILITY": "Psychiatric disorders",
    "AGGRESSION": "Psychiatric disorders",
    "PSYCHOTIC DISORDER": "Psychiatric disorders",
    "MOOD SWINGS": "Psychiatric disorders",
    "DELIRIUM": "Psychiatric disorders",
    # Gastrointestinal
    "NAUSEA": "Gastrointestinal disorders",
    "VOMITING": "Gastrointestinal disorders",
    "DIARRHOEA": "Gastrointestinal disorders",
    "CONSTIPATION": "Gastrointestinal disorders",
    "ABDOMINAL PAIN": "Gastrointestinal disorders",
    "ABDOMINAL PAIN UPPER": "Gastrointestinal disorders",
    "DYSPEPSIA": "Gastrointestinal disorders",
    "GASTROINTESTINAL HAEMORRHAGE": "Gastrointestinal disorders",
    "GASTRIC ULCER": "Gastrointestinal disorders",
    "DUODENAL ULCER": "Gastrointestinal disorders",
    "PANCREATITIS": "Gastrointestinal disorders",
    "PANCREATITIS ACUTE": "Gastrointestinal disorders",
    "DRY MOUTH": "Gastrointestinal disorders",
    "ABDOMINAL DISCOMFORT": "Gastrointestinal disorders",
    "GASTROOESOPHAGEAL REFLUX DISEASE": "Gastrointestinal disorders",
    "FLATULENCE": "Gastrointestinal disorders",
    "DYSPHAGIA": "Gastrointestinal disorders",
    "MELAENA": "Gastrointestinal disorders",
    "HAEMATEMESIS": "Gastrointestinal disorders",
    "INTESTINAL PERFORATION": "Gastrointestinal disorders",
    "COLITIS": "Gastrointestinal disorders",
    "GASTRITIS": "Gastrointestinal disorders",
    "ABDOMINAL DISTENSION": "Gastrointestinal disorders",
    # Hepatobiliary
    "HEPATITIS": "Hepatobiliary disorders",
    "HEPATIC FAILURE": "Hepatobiliary disorders",
    "HEPATOTOXICITY": "Hepatobiliary disorders",
    "JAUNDICE": "Hepatobiliary disorders",
    "HEPATIC FUNCTION ABNORMAL": "Hepatobiliary disorders",
    "LIVER DISORDER": "Hepatobiliary disorders",
    "CHOLESTASIS": "Hepatobiliary disorders",
    "LIVER INJURY": "Hepatobiliary disorders",
    "DRUG-INDUCED LIVER INJURY": "Hepatobiliary disorders",
    "HEPATIC ENZYME INCREASED": "Investigations",
    "ALANINE AMINOTRANSFERASE INCREASED": "Investigations",
    "ASPARTATE AMINOTRANSFERASE INCREASED": "Investigations",
    "BLOOD BILIRUBIN INCREASED": "Investigations",
    # Renal
    "RENAL FAILURE": "Renal and urinary disorders",
    "ACUTE KIDNEY INJURY": "Renal and urinary disorders",
    "RENAL FAILURE ACUTE": "Renal and urinary disorders",
    "RENAL IMPAIRMENT": "Renal and urinary disorders",
    "NEPHROPATHY TOXIC": "Renal and urinary disorders",
    "HAEMATURIA": "Renal and urinary disorders",
    "URINARY RETENTION": "Renal and urinary disorders",
    "URINARY INCONTINENCE": "Renal and urinary disorders",
    "BLOOD CREATININE INCREASED": "Investigations",
    "PROTEINURIA": "Renal and urinary disorders",
    "NEPHROLITHIASIS": "Renal and urinary disorders",
    "CHRONIC KIDNEY DISEASE": "Renal and urinary disorders",
    # Musculoskeletal
    "RHABDOMYOLYSIS": "Musculoskeletal and connective tissue disorders",
    "MYALGIA": "Musculoskeletal and connective tissue disorders",
    "ARTHRALGIA": "Musculoskeletal and connective tissue disorders",
    "BACK PAIN": "Musculoskeletal and connective tissue disorders",
    "MUSCLE SPASMS": "Musculoskeletal and connective tissue disorders",
    "MUSCULAR WEAKNESS": "Musculoskeletal and connective tissue disorders",
    "PAIN IN EXTREMITY": "Musculoskeletal and connective tissue disorders",
    "OSTEONECROSIS OF JAW": "Musculoskeletal and connective tissue disorders",
    "TENDON RUPTURE": "Musculoskeletal and connective tissue disorders",
    "MYOPATHY": "Musculoskeletal and connective tissue disorders",
    "OSTEOPOROSIS": "Musculoskeletal and connective tissue disorders",
    "BONE PAIN": "Musculoskeletal and connective tissue disorders",
    "MUSCLE DISORDER": "Musculoskeletal and connective tissue disorders",
    "BLOOD CREATINE PHOSPHOKINASE INCREASED": "Investigations",
    # Skin
    "RASH": "Skin and subcutaneous tissue disorders",
    "PRURITUS": "Skin and subcutaneous tissue disorders",
    "URTICARIA": "Skin and subcutaneous tissue disorders",
    "ALOPECIA": "Skin and subcutaneous tissue disorders",
    "HYPERHIDROSIS": "Skin and subcutaneous tissue disorders",
    "ERYTHEMA": "Skin and subcutaneous tissue disorders",
    "STEVENS-JOHNSON SYNDROME": "Skin and subcutaneous tissue disorders",
    "TOXIC EPIDERMAL NECROLYSIS": "Skin and subcutaneous tissue disorders",
    "ANGIOEDEMA": "Skin and subcutaneous tissue disorders",
    "DERMATITIS": "Skin and subcutaneous tissue disorders",
    "PHOTOSENSITIVITY REACTION": "Skin and subcutaneous tissue disorders",
    "SKIN EXFOLIATION": "Skin and subcutaneous tissue disorders",
    "BLISTER": "Skin and subcutaneous tissue disorders",
    "RASH PRURITIC": "Skin and subcutaneous tissue disorders",
    "ECCHYMOSIS": "Skin and subcutaneous tissue disorders",
    "NIGHT SWEATS": "Skin and subcutaneous tissue disorders",
    # Respiratory
    "DYSPNOEA": "Respiratory, thoracic and mediastinal disorders",
    "COUGH": "Respiratory, thoracic and mediastinal disorders",
    "PULMONARY EMBOLISM": "Respiratory, thoracic and mediastinal disorders",
    "PNEUMONITIS": "Respiratory, thoracic and mediastinal disorders",
    "INTERSTITIAL LUNG DISEASE": "Respiratory, thoracic and mediastinal disorders",
    "RESPIRATORY FAILURE": "Respiratory, thoracic and mediastinal disorders",
    "ASTHMA": "Respiratory, thoracic and mediastinal disorders",
    "BRONCHOSPASM": "Respiratory, thoracic and mediastinal disorders",
    "PULMONARY FIBROSIS": "Respiratory, thoracic and mediastinal disorders",
    "EPISTAXIS": "Respiratory, thoracic and mediastinal disorders",
    "PLEURAL EFFUSION": "Respiratory, thoracic and mediastinal disorders",
    "WHEEZING": "Respiratory, thoracic and mediastinal disorders",
    "PULMONARY OEDEMA": "Respiratory, thoracic and mediastinal disorders",
    "RESPIRATORY DISTRESS": "Respiratory, thoracic and mediastinal disorders",
    # Blood
    "ANAEMIA": "Blood and lymphatic system disorders",
    "THROMBOCYTOPENIA": "Blood and lymphatic system disorders",
    "NEUTROPENIA": "Blood and lymphatic system disorders",
    "FEBRILE NEUTROPENIA": "Blood and lymphatic system disorders",
    "LEUKOPENIA": "Blood and lymphatic system disorders",
    "PANCYTOPENIA": "Blood and lymphatic system disorders",
    "AGRANULOCYTOSIS": "Blood and lymphatic system disorders",
    "LYMPHADENOPATHY": "Blood and lymphatic system disorders",
    "COAGULOPATHY": "Blood and lymphatic system disorders",
    "PLATELET COUNT DECREASED": "Investigations",
    "HAEMOGLOBIN DECREASED": "Investigations",
    "WHITE BLOOD CELL COUNT DECREASED": "Investigations",
    "INTERNATIONAL NORMALISED RATIO INCREASED": "Investigations",
    # Immune
    "HYPERSENSITIVITY": "Immune system disorders",
    "DRUG HYPERSENSITIVITY": "Immune system disorders",
    "ANAPHYLACTIC REACTION": "Immune system disorders",
    "ANAPHYLACTIC SHOCK": "Immune system disorders",
    "ANAPHYLACTOID REACTION": "Immune system disorders",
    "SEASONAL ALLERGY": "Immune system disorders",
    # Infections
    "PNEUMONIA": "Infections and infestations",
    "SEPSIS": "Infections and infestations",
    "URINARY TRACT INFECTION": "Infections and infestations",
    "INFECTION": "Infections and infestations",
    "NASOPHARYNGITIS": "Infections and infestations",
    "UPPER RESPIRATORY TRACT INFECTION": "Infections and infestations",
    "INFLUENZA": "Infections and infestations",
    "HERPES ZOSTER": "Infections and infestations",
    "CELLULITIS": "Infections and infestations",
    "SEPTIC SHOCK": "Infections and infestations",
    "COVID-19": "Infections and infestations",
    "BRONCHITIS": "Infections and infestations",
    "SINUSITIS": "Infections and infestations",
    "CLOSTRIDIUM DIFFICILE COLITIS": "Infections and infestations",
    # Metabolism
    "HYPOGLYCAEMIA": "Metabolism and nutrition disorders",
    "HYPERGLYCAEMIA": "Metabolism and nutrition disorders",
    "DECREASED APPETITE": "Metabolism and nutrition disorders",
    "DEHYDRATION": "Metabolism and nutrition disorders",
    "HYPOKALAEMIA": "Metabolism and nutrition disorders",
    "HYPONATRAEMIA": "Metabolism and nutrition disorders",
    "DIABETES MELLITUS": "Metabolism and nutrition disorders",
    "LACTIC ACIDOSIS": "Metabolism and nutrition disorders",
    "DIABETIC KETOACIDOSIS": "Metabolism and nutrition disorders",
    "HYPERKALAEMIA": "Metabolism and nutrition disorders",
    "FLUID RETENTION": "Metabolism and nutrition disorders",
    "HYPERLIPIDAEMIA": "Metabolism and nutrition disorders",
    "BLOOD GLUCOSE INCREASED": "Investigations",
    "WEIGHT INCREASED": "Investigations",
    "WEIGHT DECREASED": "Investigations",
    # Endocrine
    "HYPOTHYROIDISM": "Endocrine disorders",
    "HYPERTHYROIDISM": "Endocrine disorders",
    "ADRENAL INSUFFICIENCY": "Endocrine disorders",
    "CUSHINGOID": "Endocrine disorders",
    # Eye / Ear
    "VISION BLURRED": "Eye disorders",
    "VISUAL IMPAIRMENT": "Eye disorders",
    "CATARACT": "Eye disorders",
    "BLINDNESS": "Eye disorders",
    "DRY EYE": "Eye disorders",
    "GLAUCOMA": "Eye disorders",
    "TINNITUS": "Ear and labyrinth disorders",
    "VERTIGO": "Ear and labyrinth disorders",
    "DEAFNESS": "Ear and labyrinth disorders",
    "HYPOACUSIS": "Ear and labyrinth disorders",
    # Neoplasms
    "NEOPLASM MALIGNANT": "Neoplasms benign, malignant and unspecified",
    "BREAST CANCER": "Neoplasms benign, malignant and unspecified",
    "LYMPHOMA": "Neoplasms benign, malignant and unspecified",
    "LUNG NEOPLASM MALIGNANT": "Neoplasms benign, malignant and unspecified",
    "BLADDER CANCER": "Neoplasms benign, malignant and unspecified",
    "PANCREATIC CARCINOMA": "Neoplasms benign, malignant and unspecified",
    "ACUTE MYELOID LEUKAEMIA": "Neoplasms benign, malignant and unspecified",
    "SKIN CANCER": "Neoplasms benign, malignant and unspecified",
    "PROSTATE CANCER": "Neoplasms benign, malignant and unspecified",
    "COLON CANCER": "Neoplasms benign, malignant and unspecified",
    # Reproductive / pregnancy
    "ERECTILE DYSFUNCTION": "Reproductive system and breast disorders",
    "GYNAECOMASTIA": "Reproductive system and breast disorders",
    "MENSTRUATION IRREGULAR": "Reproductive system and breast disorders",
    "ABORTION SPONTANEOUS": "Pregnancy, puerperium and perinatal conditions",
    "PREMATURE BABY": "Pregnancy, puerperium and perinatal conditions",
    "FOETAL EXPOSURE DURING PREGNANCY": "Pregnancy, puerperium and perinatal conditions",
    "MATERNAL EXPOSURE DURING PREGNANCY": "Pregnancy, puerperium and perinatal conditions",
    # Congenital
    "CONGENITAL ANOMALY": "Congenital, familial and genetic disorders",
    # General disorders
    "FATIGUE": "General disorders and administration site conditions",
    "ASTHENIA": "General disorders and administration site conditions",
    "PYREXIA": "General disorders and administration site conditions",
    "MALAISE": "General disorders and administration site conditions",
    "OEDEMA PERIPHERAL": "General disorders and administration site conditions",
    "OEDEMA": "General disorders and administration site conditions",
    "CHEST PAIN": "General disorders and administration site conditions",
    "PAIN": "General disorders and administration site conditions",
    "FEELING ABNORMAL": "General disorders and administration site conditions",
    "CHILLS": "General disorders and administration site conditions",
    "INJECTION SITE PAIN": "General disorders and administration site conditions",
    "INJECTION SITE REACTION": "General disorders and administration site conditions",
    "INJECTION SITE ERYTHEMA": "General disorders and administration site conditions",
    "GAIT DISTURBANCE": "General disorders and administration site conditions",
    "DEATH": "General disorders and administration site conditions",
    "SUDDEN DEATH": "General disorders and administration site conditions",
    "GENERALISED OEDEMA": "General disorders and administration site conditions",
    "MULTIPLE ORGAN DYSFUNCTION SYNDROME": "General disorders and administration site conditions",
    "DRUG WITHDRAWAL SYNDROME": "General disorders and administration site conditions",
    "THERAPEUTIC RESPONSE DECREASED": "General disorders and administration site conditions",
    "FEELING HOT": "General disorders and administration site conditions",
    "PERIPHERAL SWELLING": "General disorders and administration site conditions",
    # Injury / procedural
    "FALL": "Injury, poisoning and procedural complications",
    "OVERDOSE": "Injury, poisoning and procedural complications",
    "INTENTIONAL OVERDOSE": "Injury, poisoning and procedural complications",
    "ACCIDENTAL OVERDOSE": "Injury, poisoning and procedural complications",
    "TOXICITY TO VARIOUS AGENTS": "Injury, poisoning and procedural complications",
    "CONTUSION": "Injury, poisoning and procedural complications",
    "HIP FRACTURE": "Injury, poisoning and procedural complications",
    "FRACTURE": "Injury, poisoning and procedural complications",
    "ACCIDENTAL EXPOSURE TO PRODUCT": "Injury, poisoning and procedural complications",
    "INFUSION RELATED REACTION": "Injury, poisoning and procedural complications",
    "PROCEDURAL PAIN": "Injury, poisoning and procedural complications",
    # Product issues / usage (administrative)
    "DRUG INEFFECTIVE": "Product / usage issues",
    "OFF LABEL USE": "Product / usage issues",
    "PRODUCT USED FOR UNKNOWN INDICATION": "Product / usage issues",
    "DRUG INTERACTION": "Product / usage issues",
    "DRUG DOSE OMISSION": "Product / usage issues",
    "INCORRECT DOSE ADMINISTERED": "Product / usage issues",
    "MEDICATION ERROR": "Product / usage issues",
    "PRODUCT QUALITY ISSUE": "Product / usage issues",
    "PRODUCT USE ISSUE": "Product / usage issues",
    "WRONG TECHNIQUE IN PRODUCT USAGE PROCESS": "Product / usage issues",
    "INTENTIONAL PRODUCT USE ISSUE": "Product / usage issues",
    "TREATMENT NONCOMPLIANCE": "Product / usage issues",
    "PRODUCT SUBSTITUTION ISSUE": "Product / usage issues",
    "INAPPROPRIATE SCHEDULE OF PRODUCT ADMINISTRATION": "Product / usage issues",
    "EXPIRED PRODUCT ADMINISTERED": "Product / usage issues",
    # Surgical / social
    "HOSPITALISATION": "Surgical and medical procedures",
    "SURGERY": "Surgical and medical procedures",
    "CORONARY ARTERY BYPASS": "Surgical and medical procedures",
    "IMPAIRED WORK ABILITY": "Social circumstances",
    "DISABILITY": "Social circumstances",
}

# Ordered keyword heuristics for anything not in the curated map (first match wins).
KEYWORD_RULES: list[tuple[tuple[str, ...], str]] = [
    (("MYOCARDIAL", "CARDIAC", "CORONARY", "ARRHYTHM", "TACHYCARD", "BRADYCARD", "FIBRILLATION", "ANGINA", "HEART"), "Cardiac disorders"),
    (("HEPAT", "LIVER", "BILIAR", "CHOLESTA", "JAUNDICE", "BILIRUBIN"), "Hepatobiliary disorders"),
    (("RENAL", "NEPHR", "KIDNEY", "URINARY", "URIN", "BLADDER", "CREATININE"), "Renal and urinary disorders"),
    (("THROMBO", "EMBOL", "HAEMORRHAG", "HEMORRHAG", "BLEED", "HYPERTENS", "HYPOTENS", "VASCUL", "VEIN", "ARTER", "ANEURYSM"), "Vascular disorders"),
    (("PULMONARY", "LUNG", "RESPIRAT", "BRONCH", "PNEUMONIT", "DYSPNOEA", "APNOEA", "PLEUR", "COUGH"), "Respiratory, thoracic and mediastinal disorders"),
    (("PNEUMONIA", "SEPSIS", "INFECTION", "INFECTIOUS", "VIRAL", "BACTERIAL", "FUNGAL", "ABSCESS", "CANDID", "HERPES", "CELLULITIS"), "Infections and infestations"),
    (("CARCINOMA", "CANCER", "NEOPLASM", "TUMOUR", "TUMOR", "LYMPHOMA", "LEUKAEMIA", "LEUKEMIA", "MELANOMA", "SARCOMA", "METASTA"), "Neoplasms benign, malignant and unspecified"),
    (("GASTR", "INTESTIN", "ABDOMINAL", "VOMIT", "NAUSEA", "DIARRH", "CONSTIPAT", "COLITIS", "PANCREAT", "OESOPHAG", "ESOPHAG", "BOWEL", "DYSPEPS", "ULCER"), "Gastrointestinal disorders"),
    (("SEIZURE", "CONVULS", "NEURO", "CEREBR", "STROKE", "HEADACHE", "DIZZ", "TREMOR", "PARAESTHES", "SOMNOLEN", "DYSKINES", "ENCEPHAL", "MYELIT", "COGNITIVE", "MEMORY", "SYNCOPE", "ATAXIA", "PARALYS", "MIGRAINE"), "Nervous system disorders"),
    (("SUICID", "DEPRESS", "ANXIETY", "PSYCH", "HALLUCIN", "INSOMNIA", "AGITAT", "CONFUS", "DELIRI", "MANIA", "MOOD", "PANIC", "DELUSION"), "Psychiatric disorders"),
    (("RHABDOMYOLYSIS", "MYALGIA", "ARTHR", "MUSCLE", "MUSCUL", "TENDON", "BONE", "OSTEO", "JOINT", "MYOPATHY", "BACK PAIN"), "Musculoskeletal and connective tissue disorders"),
    (("RASH", "PRURIT", "URTICARIA", "DERMAT", "SKIN", "ERYTHEM", "ALOPECIA", "SWEAT", "HIDROSIS", "ECZEMA", "PSORIA", "BLISTER", "ANGIOEDEMA", "NECROLYSIS", "ACNE"), "Skin and subcutaneous tissue disorders"),
    (("ANAEMIA", "ANEMIA", "THROMBOCYTOP", "NEUTROP", "LEUKOP", "CYTOPENIA", "LYMPHADENOPATHY", "COAGUL", "PLATELET", "HAEMATOLOG"), "Blood and lymphatic system disorders"),
    (("HYPERSENSITIV", "ANAPHYLA", "ALLERG", "IMMUN"), "Immune system disorders"),
    (("GLYCAEMIA", "GLYCEMIA", "DIABET", "KALAEMIA", "NATRAEMIA", "CALCAEMIA", "APPETITE", "DEHYDRAT", "ACIDOSIS", "LIPID", "CHOLESTEROL", "OBESITY", "NUTRITION", "MAGNESAEMIA"), "Metabolism and nutrition disorders"),
    (("THYROID", "ADRENAL", "CUSHING", "PITUITAR", "HORMONE", "ENDOCRIN"), "Endocrine disorders"),
    (("VISION", "VISUAL", "EYE", "OCULAR", "RETIN", "CATARACT", "BLIND", "OPTIC", "GLAUCOMA"), "Eye disorders"),
    (("TINNITUS", "VERTIGO", "HEARING", "DEAF", "EAR ", "ACUSIS"), "Ear and labyrinth disorders"),
    (("PREGNAN", "ABORTION", "FOETAL", "FETAL", "NEONATAL", "PREMATURE", "BIRTH", "STILLBIRTH"), "Pregnancy, puerperium and perinatal conditions"),
    (("ERECTILE", "MENSTRU", "BREAST", "OVARIAN", "UTERINE", "TESTIC", "PROSTAT", "VAGINAL", "LIBIDO", "GYNAECOMAST"), "Reproductive system and breast disorders"),
    (("CONGENITAL", "GENETIC", "HEREDITARY"), "Congenital, familial and genetic disorders"),
    (("OVERDOSE", "FALL", "FRACTURE", "INJURY", "POISON", "EXPOSURE", "PROCEDURAL", "INFUSION RELATED", "TOXICITY", "WOUND", "CONTUSION", "ACCIDENT"), "Injury, poisoning and procedural complications"),
    (("INCREASED", "DECREASED", "ABNORMAL", "TEST", "ELECTROCARDIOGRAM", "BLOOD ", "WEIGHT", "COUNT", "LEVEL"), "Investigations"),
    (("PRODUCT", "DRUG INEFFECTIVE", "OFF LABEL", "DOSE", "MEDICATION ERROR", "NONCOMPLIANCE", "INDICATION", "DEVICE"), "Product / usage issues"),
    (("SURGERY", "SURGICAL", "PROCEDURE", "HOSPITALISATION", "HOSPITALIZATION", "TRANSPLANT", "BYPASS", "DIALYSIS"), "Surgical and medical procedures"),
    (("FATIGUE", "ASTHENIA", "PYREXIA", "FEVER", "MALAISE", "OEDEMA", "EDEMA", "PAIN", "DEATH", "CHILLS", "INJECTION SITE", "FEELING", "SWELLING", "DISCOMFORT", "GAIT", "INFLAMMATION", "WITHDRAWAL"), "General disorders and administration site conditions"),
]

UNCLASSIFIED = "Unclassified"


def assign_soc(term: str) -> tuple[str, str]:
    """Return (system_organ_class, method) where method is 'curated' | 'heuristic' | 'none'."""
    t = term.strip().upper()
    if t in PT_TO_SOC:
        return PT_TO_SOC[t], "curated"
    padded = f" {t} "
    for keywords, soc in KEYWORD_RULES:
        if any(k in padded for k in keywords):
            return soc, "heuristic"
    return UNCLASSIFIED, "none"


def cluster_signals(table: pd.DataFrame, only_signals: bool = True, include_administrative: bool = False) -> pd.DataFrame:
    """Aggregate a scan table into one row per System Organ Class.

    Columns: soc, n_reactions, n_cases, max_prr, median_prr, strongest_reaction, reactions,
    curated_share (fraction of reactions mapped from the curated list, as a confidence hint).
    """
    empty = pd.DataFrame(
        columns=["soc", "n_reactions", "n_cases", "max_prr", "median_prr", "strongest_reaction", "reactions", "curated_share"]
    )
    if table is None or table.empty:
        return empty
    df = table.copy()
    if only_signals:
        df = df[df["is_signal"].astype(bool)]
    if not include_administrative:
        df = df[~df["is_administrative"].astype(bool)]
    if df.empty:
        return empty

    socs = df["reaction"].map(lambda r: assign_soc(r))
    df = df.assign(soc=[s for s, _ in socs], soc_method=[m for _, m in socs])

    groups = []
    for soc, g in df.groupby("soc"):
        g = g.sort_values("prr", ascending=False)
        groups.append(
            {
                "soc": soc,
                "n_reactions": int(len(g)),
                "n_cases": int(g["n_cases"].sum()),
                "max_prr": float(g["prr"].max()),
                "median_prr": float(g["prr"].median()),
                "strongest_reaction": g.iloc[0]["reaction"],
                "reactions": list(g["reaction"]),
                "curated_share": float((g["soc_method"] == "curated").mean()),
            }
        )
    out = pd.DataFrame(groups).sort_values(["n_cases", "max_prr"], ascending=False).reset_index(drop=True)
    return out
