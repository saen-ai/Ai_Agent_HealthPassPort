"""Test the PDF and Vision services."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pdf_service import PDFService
from app.data.biomarker_mapping import (
    standardize_biomarker_name,
    get_biomarker_category,
    get_flag,
    get_reference_range,
)


def test_biomarker_mapping():
    """Test biomarker name standardization."""
    print("\n=== Testing Biomarker Mapping ===")
    
    test_cases = [
        ("Hemoglobin", "hemoglobin", "CBC"),
        ("HbA1c", "hba1c", "METABOLIC"),
        ("WBC", "wbc", "CBC"),
        ("Total Cholesterol", "cholesterol_total", "LIPID"),
        ("LDL", "ldl", "LIPID"),
        ("TSH", "tsh", "THYROID"),
        ("Vitamin D", "vitamin_d", "VITAMIN"),
        ("ALT", "alt", "LIVER"),
        ("Unknown Test", "unknown_test", "OTHER"),
    ]
    
    all_passed = True
    for original, expected_name, expected_category in test_cases:
        std_name = standardize_biomarker_name(original)
        category = get_biomarker_category(std_name)
        
        name_match = std_name == expected_name
        cat_match = category == expected_category
        
        status = "✓" if (name_match and cat_match) else "✗"
        print(f"  {status} '{original}' -> '{std_name}' ({category})")
        
        if not (name_match and cat_match):
            all_passed = False
    
    return all_passed


def test_reference_ranges():
    """Test reference range lookups and flagging."""
    print("\n=== Testing Reference Ranges & Flags ===")
    
    test_cases = [
        # (biomarker, value, gender, expected_flag)
        ("hemoglobin", 14.0, "male", None),              # Normal
        ("hemoglobin", 12.5, "male", "LOW"),             # Low (just below 13.5)
        ("hemoglobin", 10.0, "male", "CRITICAL_LOW"),    # Critical low (>20% below)
        ("hemoglobin", 18.0, "male", "HIGH"),            # High (just above 17.5)
        ("hemoglobin", 22.0, "male", "CRITICAL_HIGH"),   # Critical high (>20% above)
        ("glucose", 95, None, None),                     # Normal fasting
        ("glucose", 105, None, "HIGH"),                  # High
        ("glucose", 130, None, "CRITICAL_HIGH"),         # Critical high
        ("cholesterol_total", 180, None, None),          # Normal
        ("cholesterol_total", 210, None, "HIGH"),        # High
    ]
    
    all_passed = True
    for biomarker, value, gender, expected_flag in test_cases:
        ref_min, ref_max = get_reference_range(biomarker, gender)
        flag = get_flag(biomarker, value, gender)
        
        status = "✓" if flag == expected_flag else "✗"
        print(f"  {status} {biomarker}={value} -> flag={flag} (expected: {expected_flag})")
        print(f"      Reference: {ref_min} - {ref_max}")
        
        if flag != expected_flag:
            all_passed = False
    
    return all_passed


def test_pdf_service():
    """Test PDF service methods (without actual PDF)."""
    print("\n=== Testing PDF Service ===")
    
    # Test with non-existent file
    fake_path = "/tmp/nonexistent.pdf"
    
    print(f"  Testing with non-existent file...")
    
    is_encrypted = PDFService.check_encryption(fake_path)
    print(f"  ✓ check_encryption handles missing file: {is_encrypted}")
    
    text = PDFService.extract_text(fake_path)
    print(f"  ✓ extract_text handles missing file: '{text}'")
    
    tables = PDFService.extract_tables(fake_path)
    print(f"  ✓ extract_tables handles missing file: {tables}")
    
    page_count = PDFService.get_page_count(fake_path)
    print(f"  ✓ get_page_count handles missing file: {page_count}")
    
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("AI Health Passport - Service Tests")
    print("=" * 50)
    
    results = []
    
    results.append(("Biomarker Mapping", test_biomarker_mapping()))
    results.append(("Reference Ranges", test_reference_ranges()))
    results.append(("PDF Service", test_pdf_service()))
    
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())

