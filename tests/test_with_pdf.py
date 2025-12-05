"""Test extraction with an actual PDF file."""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pdf_service import PDFService
from app.services.vision_service import VisionService
from app.data.biomarker_mapping import standardize_biomarker_name, get_biomarker_category, get_flag
from app.core.logging import logger


def test_pdf_extraction(pdf_path: str):
    """Test text extraction from a PDF file."""
    print(f"\n=== Testing PDF Extraction ===")
    print(f"PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"✗ File not found: {pdf_path}")
        return False
    
    # Check encryption
    is_encrypted = PDFService.check_encryption(pdf_path)
    print(f"  Encrypted: {is_encrypted}")
    
    if is_encrypted:
        print("  ✗ PDF is encrypted - need password")
        return False
    
    # Get page count
    page_count = PDFService.get_page_count(pdf_path)
    print(f"  Pages: {page_count}")
    
    # Extract text
    text = PDFService.extract_text(pdf_path)
    print(f"  Text extracted: {len(text)} characters")
    if text:
        print(f"  First 500 chars:\n{'-'*40}")
        print(text[:500])
        print(f"{'-'*40}")
    
    # Extract tables
    tables = PDFService.extract_tables(pdf_path)
    print(f"  Tables found: {len(tables)}")
    for i, table in enumerate(tables[:3]):  # Show first 3 tables
        print(f"\n  Table {i+1} ({len(table)} rows):")
        for row in table[:5]:  # Show first 5 rows
            print(f"    {row}")
    
    # Check if needs vision
    needs_vision = PDFService.has_images_or_scanned(pdf_path)
    print(f"\n  Needs Vision API: {needs_vision}")
    
    return True


def test_vision_extraction(pdf_path: str, output_dir: str = "/tmp/test_vision"):
    """Test Vision API extraction from PDF images."""
    print(f"\n=== Testing Vision API Extraction ===")
    
    if not os.path.exists(pdf_path):
        print(f"✗ File not found: {pdf_path}")
        return False
    
    # Convert PDF to images
    print(f"  Converting PDF to images...")
    image_paths = PDFService.pdf_to_images(pdf_path, output_dir)
    print(f"  Created {len(image_paths)} images")
    
    if not image_paths:
        print("  ✗ No images created")
        return False
    
    # Extract from first image only (to save API cost)
    print(f"\n  Extracting from first image using GPT-4o Vision...")
    vision_service = VisionService()
    result = vision_service.extract_from_image(image_paths[0])
    
    if "error" in result:
        print(f"  ✗ Vision API error: {result['error']}")
        return False
    
    print(f"\n  Vision API Result:")
    print(f"    Lab Name: {result.get('lab_name')}")
    print(f"    Report Date: {result.get('report_date')}")
    print(f"    Report Type: {result.get('report_type')}")
    print(f"    Biomarkers found: {len(result.get('biomarkers', []))}")
    
    for bio in result.get('biomarkers', [])[:10]:  # Show first 10
        std_name = standardize_biomarker_name(bio.get('name', ''))
        category = get_biomarker_category(std_name)
        print(f"      - {bio.get('name')}: {bio.get('value')} {bio.get('unit')} -> {std_name} ({category})")
    
    return True


def main():
    """Run PDF tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test PDF extraction")
    parser.add_argument("pdf_path", help="Path to the PDF file to test")
    parser.add_argument("--vision", action="store_true", help="Also test Vision API extraction")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("AI Health Passport - PDF Extraction Test")
    print("=" * 50)
    
    # Test PDF extraction
    success = test_pdf_extraction(args.pdf_path)
    
    # Test Vision if requested
    if args.vision and success:
        test_vision_extraction(args.pdf_path)
    
    print("\n" + "=" * 50)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

