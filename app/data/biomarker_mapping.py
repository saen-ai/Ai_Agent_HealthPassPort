"""Biomarker name standardization and reference ranges."""

from typing import Optional, Tuple

# Mapping of biomarker aliases to standardized names with metadata
BIOMARKER_MAPPING = {
    # Complete Blood Count (CBC)
    "hemoglobin": {
        "aliases": ["Hb", "Hgb", "Haemoglobin", "HGB", "Hemoglobin"],
        "category": "CBC",
        "default_unit": "g/dL",
        "reference": {"male": (13.5, 17.5), "female": (12.0, 16.0), "default": (12.0, 17.5)},
    },
    "hematocrit": {
        "aliases": ["Hct", "HCT", "Haematocrit", "Packed Cell Volume", "PCV"],
        "category": "CBC",
        "default_unit": "%",
        "reference": {"male": (38.3, 48.6), "female": (35.5, 44.9), "default": (35.5, 48.6)},
    },
    "rbc": {
        "aliases": ["RBC", "Red Blood Cell", "Red Blood Cells", "Erythrocytes", "Red Cell Count"],
        "category": "CBC",
        "default_unit": "M/uL",
        "reference": {"male": (4.5, 5.5), "female": (4.0, 5.0), "default": (4.0, 5.5)},
    },
    "wbc": {
        "aliases": ["WBC", "White Blood Cell", "White Blood Cells", "Leukocytes", "Total WBC Count", "Total WBC"],
        "category": "CBC",
        "default_unit": "K/uL",
        "reference": {"default": (4.5, 11.0)},
    },
    "platelets": {
        "aliases": ["PLT", "Platelet", "Platelet Count", "Thrombocytes"],
        "category": "CBC",
        "default_unit": "K/uL",
        "reference": {"default": (150, 400)},
    },
    "mcv": {
        "aliases": ["MCV", "Mean Corpuscular Volume", "Mean Cell Volume"],
        "category": "CBC",
        "default_unit": "fL",
        "reference": {"default": (80, 100)},
    },
    "mch": {
        "aliases": ["MCH", "Mean Corpuscular Hemoglobin", "Mean Cell Hemoglobin"],
        "category": "CBC",
        "default_unit": "pg",
        "reference": {"default": (27, 33)},
    },
    "mchc": {
        "aliases": ["MCHC", "Mean Corpuscular Hemoglobin Concentration"],
        "category": "CBC",
        "default_unit": "g/dL",
        "reference": {"default": (31.5, 35.5)},
    },
    "rdw": {
        "aliases": ["RDW", "Red Cell Distribution Width", "RDW-CV"],
        "category": "CBC",
        "default_unit": "%",
        "reference": {"default": (11.5, 14.5)},
    },
    "neutrophils": {
        "aliases": ["Neutrophils", "Neutrophil", "Neut", "Neutro", "Absolute Neutrophil Count", "ANC"],
        "category": "CBC",
        "default_unit": "%",
        "reference": {"default": (40, 70)},
    },
    "lymphocytes": {
        "aliases": ["Lymphocytes", "Lymphocyte", "Lymph", "Absolute Lymphocyte Count", "ALC"],
        "category": "CBC",
        "default_unit": "%",
        "reference": {"default": (20, 40)},
    },
    "monocytes": {
        "aliases": ["Monocytes", "Monocyte", "Mono", "Absolute Monocyte Count"],
        "category": "CBC",
        "default_unit": "%",
        "reference": {"default": (2, 8)},
    },
    "eosinophils": {
        "aliases": ["Eosinophils", "Eosinophil", "Eos", "Absolute Eosinophil Count", "AEC"],
        "category": "CBC",
        "default_unit": "%",
        "reference": {"default": (1, 4)},
    },
    "basophils": {
        "aliases": ["Basophils", "Basophil", "Baso", "Absolute Basophil Count"],
        "category": "CBC",
        "default_unit": "%",
        "reference": {"default": (0, 2)},
    },
    
    # Lipid Panel
    "cholesterol_total": {
        "aliases": ["Total Cholesterol", "Cholesterol", "TC", "Serum Cholesterol"],
        "category": "LIPID",
        "default_unit": "mg/dL",
        "reference": {"default": (0, 200)},
    },
    "ldl": {
        "aliases": ["LDL", "LDL Cholesterol", "LDL-C", "Low Density Lipoprotein", "Bad Cholesterol"],
        "category": "LIPID",
        "default_unit": "mg/dL",
        "reference": {"default": (0, 100)},
    },
    "hdl": {
        "aliases": ["HDL", "HDL Cholesterol", "HDL-C", "High Density Lipoprotein", "Good Cholesterol"],
        "category": "LIPID",
        "default_unit": "mg/dL",
        "reference": {"male": (40, 999), "female": (50, 999), "default": (40, 999)},
    },
    "triglycerides": {
        "aliases": ["Triglycerides", "TG", "Triglyceride", "Trigs"],
        "category": "LIPID",
        "default_unit": "mg/dL",
        "reference": {"default": (0, 150)},
    },
    "vldl": {
        "aliases": ["VLDL", "VLDL Cholesterol", "Very Low Density Lipoprotein"],
        "category": "LIPID",
        "default_unit": "mg/dL",
        "reference": {"default": (5, 40)},
    },
    
    # Metabolic Panel
    "glucose": {
        "aliases": ["Glucose", "Blood Sugar", "FBS", "Fasting Blood Sugar", "Fasting Glucose", "Blood Glucose"],
        "category": "METABOLIC",
        "default_unit": "mg/dL",
        "reference": {"default": (70, 100)},
    },
    "hba1c": {
        "aliases": ["HbA1c", "A1C", "Glycated Hemoglobin", "Hemoglobin A1c", "Glycosylated Hemoglobin"],
        "category": "METABOLIC",
        "default_unit": "%",
        "reference": {"default": (4.0, 5.7)},
    },
    "bun": {
        "aliases": ["BUN", "Blood Urea Nitrogen", "Urea Nitrogen"],
        "category": "METABOLIC",
        "default_unit": "mg/dL",
        "reference": {"default": (7, 20)},
    },
    "creatinine": {
        "aliases": ["Creatinine", "Serum Creatinine", "Creat"],
        "category": "METABOLIC",
        "default_unit": "mg/dL",
        "reference": {"male": (0.7, 1.3), "female": (0.6, 1.1), "default": (0.6, 1.3)},
    },
    "sodium": {
        "aliases": ["Sodium", "Na", "Serum Sodium"],
        "category": "METABOLIC",
        "default_unit": "mEq/L",
        "reference": {"default": (136, 145)},
    },
    "potassium": {
        "aliases": ["Potassium", "K", "Serum Potassium"],
        "category": "METABOLIC",
        "default_unit": "mEq/L",
        "reference": {"default": (3.5, 5.0)},
    },
    "chloride": {
        "aliases": ["Chloride", "Cl", "Serum Chloride"],
        "category": "METABOLIC",
        "default_unit": "mEq/L",
        "reference": {"default": (98, 106)},
    },
    "co2": {
        "aliases": ["CO2", "Carbon Dioxide", "Bicarbonate", "HCO3"],
        "category": "METABOLIC",
        "default_unit": "mEq/L",
        "reference": {"default": (23, 29)},
    },
    "calcium": {
        "aliases": ["Calcium", "Ca", "Serum Calcium"],
        "category": "METABOLIC",
        "default_unit": "mg/dL",
        "reference": {"default": (8.5, 10.5)},
    },
    
    # Liver Function
    "alt": {
        "aliases": ["ALT", "SGPT", "Alanine Aminotransferase", "Alanine Transaminase"],
        "category": "LIVER",
        "default_unit": "U/L",
        "reference": {"male": (7, 56), "female": (7, 45), "default": (7, 56)},
    },
    "ast": {
        "aliases": ["AST", "SGOT", "Aspartate Aminotransferase", "Aspartate Transaminase"],
        "category": "LIVER",
        "default_unit": "U/L",
        "reference": {"default": (10, 40)},
    },
    "alp": {
        "aliases": ["ALP", "Alkaline Phosphatase", "Alk Phos"],
        "category": "LIVER",
        "default_unit": "U/L",
        "reference": {"default": (44, 147)},
    },
    "bilirubin_total": {
        "aliases": ["Total Bilirubin", "Bilirubin", "T. Bilirubin", "T.Bil"],
        "category": "LIVER",
        "default_unit": "mg/dL",
        "reference": {"default": (0.1, 1.2)},
    },
    "albumin": {
        "aliases": ["Albumin", "Serum Albumin", "Alb"],
        "category": "LIVER",
        "default_unit": "g/dL",
        "reference": {"default": (3.5, 5.0)},
    },
    "total_protein": {
        "aliases": ["Total Protein", "Protein", "Serum Protein", "TP"],
        "category": "LIVER",
        "default_unit": "g/dL",
        "reference": {"default": (6.0, 8.3)},
    },
    
    # Thyroid
    "tsh": {
        "aliases": ["TSH", "Thyroid Stimulating Hormone", "Thyrotropin"],
        "category": "THYROID",
        "default_unit": "mIU/L",
        "reference": {"default": (0.4, 4.0)},
    },
    "t3": {
        "aliases": ["T3", "Triiodothyronine", "Total T3"],
        "category": "THYROID",
        "default_unit": "ng/dL",
        "reference": {"default": (80, 200)},
    },
    "t4": {
        "aliases": ["T4", "Thyroxine", "Total T4"],
        "category": "THYROID",
        "default_unit": "ug/dL",
        "reference": {"default": (4.5, 12.0)},
    },
    "free_t4": {
        "aliases": ["Free T4", "FT4", "Free Thyroxine"],
        "category": "THYROID",
        "default_unit": "ng/dL",
        "reference": {"default": (0.8, 1.8)},
    },
    
    # Vitamins
    "vitamin_d": {
        "aliases": ["Vitamin D", "Vit D", "25-OH Vitamin D", "25-Hydroxyvitamin D", "Cholecalciferol"],
        "category": "VITAMIN",
        "default_unit": "ng/mL",
        "reference": {"default": (30, 100)},
    },
    "vitamin_b12": {
        "aliases": ["Vitamin B12", "B12", "Cobalamin", "Cyanocobalamin"],
        "category": "VITAMIN",
        "default_unit": "pg/mL",
        "reference": {"default": (200, 900)},
    },
    "folate": {
        "aliases": ["Folate", "Folic Acid", "Vitamin B9"],
        "category": "VITAMIN",
        "default_unit": "ng/mL",
        "reference": {"default": (3.0, 17.0)},
    },
    "iron": {
        "aliases": ["Iron", "Serum Iron", "Fe"],
        "category": "VITAMIN",
        "default_unit": "ug/dL",
        "reference": {"male": (65, 175), "female": (50, 170), "default": (50, 175)},
    },
    "ferritin": {
        "aliases": ["Ferritin", "Serum Ferritin"],
        "category": "VITAMIN",
        "default_unit": "ng/mL",
        "reference": {"male": (20, 250), "female": (10, 120), "default": (10, 250)},
    },
}


def standardize_biomarker_name(name: str) -> str:
    """
    Convert any biomarker name to its standardized form.
    Returns the standardized name or a cleaned version of the original.
    """
    name_lower = name.lower().strip()
    
    # Check exact match first
    if name_lower in BIOMARKER_MAPPING:
        return name_lower
    
    # Check aliases
    for std_name, info in BIOMARKER_MAPPING.items():
        if any(alias.lower() == name_lower for alias in info["aliases"]):
            return std_name
    
    # If not found, return cleaned version of original
    return name_lower.replace(" ", "_").replace("-", "_")


def get_biomarker_category(standardized_name: str) -> str:
    """Get the category for a standardized biomarker name."""
    if standardized_name in BIOMARKER_MAPPING:
        return BIOMARKER_MAPPING[standardized_name]["category"]
    return "OTHER"


def get_reference_range(
    standardized_name: str,
    gender: Optional[str] = None
) -> Tuple[Optional[float], Optional[float]]:
    """
    Get reference range for a biomarker.
    Returns (min, max) or (None, None) if not found.
    """
    if standardized_name not in BIOMARKER_MAPPING:
        return None, None
    
    ref = BIOMARKER_MAPPING[standardized_name]["reference"]
    
    # Try gender-specific first
    if gender and gender.lower() in ref:
        return ref[gender.lower()]
    
    # Fall back to default
    if "default" in ref:
        return ref["default"]
    
    return None, None


def get_flag(
    standardized_name: str,
    value: float,
    ref_min: Optional[float] = None,
    ref_max: Optional[float] = None,
    gender: Optional[str] = None
) -> Optional[str]:
    """
    Determine flag (HIGH/LOW) based on reference range.
    If ref_min/ref_max are not provided, looks up from biomarker mapping.
    Returns None if within range or range not found.
    """
    # Use provided reference range or look up
    if ref_min is None or ref_max is None:
        ref_min, ref_max = get_reference_range(standardized_name, gender)
    
    if ref_min is None or ref_max is None:
        return None
    
    if value < ref_min:
        # Check for critical low (more than 20% below min)
        if value < ref_min * 0.8:
            return "CRITICAL_LOW"
        return "LOW"
    
    if value > ref_max:
        # Check for critical high (more than 20% above max)
        if value > ref_max * 1.2:
            return "CRITICAL_HIGH"
        return "HIGH"
    
    return None

