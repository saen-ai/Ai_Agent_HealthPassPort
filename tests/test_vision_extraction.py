"""Test Vision API extraction with real lab report images."""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vision_service import VisionService
from app.data.biomarker_mapping import standardize_biomarker_name, get_biomarker_category, get_flag
from app.core.logging import logger


def test_single_image(image_path: str, save_json: bool = True):
    """Test extraction from a single image."""
    print(f"\n{'='*60}")
    print(f"Testing: {Path(image_path).name}")
    print(f"{'='*60}")
    
    if not os.path.exists(image_path):
        print(f"✗ File not found: {image_path}")
        return None
    
    # Initialize Vision Service
    vision_service = VisionService()
    
    # Extract data
    print("Extracting with GPT-4o Vision...")
    result = vision_service.extract_from_image(image_path)
    
    if "error" in result:
        print(f"✗ Error: {result['error']}")
        return None
    
    # Display results
    print(f"\n📋 Report Metadata:")
    print(f"   Lab Name: {result.get('lab_name', 'N/A')}")
    print(f"   Report Date: {result.get('report_date', 'N/A')}")
    print(f"   Report Type: {result.get('report_type', 'N/A')}")
    
    biomarkers = result.get('biomarkers', [])
    print(f"\n🔬 Biomarkers Found: {len(biomarkers)}")
    print("-" * 60)
    
    # Process and display biomarkers
    processed_biomarkers = []
    for bio in biomarkers:
        name = bio.get('name', '')
        value = bio.get('value')
        unit = bio.get('unit', '')
        ref_min = bio.get('reference_min')
        ref_max = bio.get('reference_max')
        
        # Standardize
        std_name = standardize_biomarker_name(name)
        category = get_biomarker_category(std_name)
        
        # Get flag
        flag = None
        if value is not None and isinstance(value, (int, float)):
            flag = get_flag(std_name, float(value))
            if not flag and ref_min is not None and ref_max is not None:
                # Use report's reference range
                if value < ref_min:
                    flag = "LOW"
                elif value > ref_max:
                    flag = "HIGH"
        
        # Display
        flag_emoji = ""
        if flag:
            if "HIGH" in flag:
                flag_emoji = "🔴"
            elif "LOW" in flag:
                flag_emoji = "🔵"
        
        ref_range = ""
        if ref_min is not None and ref_max is not None:
            ref_range = f"({ref_min}-{ref_max})"
        
        print(f"   {flag_emoji} {name}: {value} {unit} {ref_range}")
        print(f"      → {std_name} [{category}]")
        
        processed_biomarkers.append({
            "original_name": name,
            "standardized_name": std_name,
            "category": category,
            "value": value,
            "unit": unit,
            "reference_min": ref_min,
            "reference_max": ref_max,
            "flag": flag,
            "is_abnormal": flag is not None,
        })
    
    # Summary
    abnormal_count = sum(1 for b in processed_biomarkers if b['is_abnormal'])
    print(f"\n📊 Summary:")
    print(f"   Total Biomarkers: {len(processed_biomarkers)}")
    print(f"   Abnormal Values: {abnormal_count}")
    
    # Save JSON
    if save_json:
        output_path = image_path.replace('.png', '_extracted.json')
        output_data = {
            "source_image": Path(image_path).name,
            "lab_name": result.get('lab_name'),
            "report_date": result.get('report_date'),
            "report_type": result.get('report_type'),
            "biomarkers": processed_biomarkers,
            "summary": {
                "total": len(processed_biomarkers),
                "abnormal": abnormal_count,
            }
        }
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n💾 Saved to: {Path(output_path).name}")
    
    return processed_biomarkers


def test_all_images():
    """Test extraction from all PNG images in tests folder."""
    tests_dir = Path(__file__).parent
    image_files = list(tests_dir.glob("*.png"))
    
    print(f"Found {len(image_files)} image files")
    
    all_results = {}
    
    for image_path in image_files:
        result = test_single_image(str(image_path))
        if result:
            all_results[image_path.name] = result
    
    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    
    total_biomarkers = sum(len(r) for r in all_results.values())
    total_abnormal = sum(sum(1 for b in r if b['is_abnormal']) for r in all_results.values())
    
    print(f"Images Processed: {len(all_results)}")
    print(f"Total Biomarkers Extracted: {total_biomarkers}")
    print(f"Total Abnormal Values: {total_abnormal}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Vision API extraction")
    parser.add_argument("--image", help="Path to specific image to test")
    parser.add_argument("--all", action="store_true", help="Test all images in tests folder")
    parser.add_argument("--no-save", action="store_true", help="Don't save JSON output")
    
    args = parser.parse_args()
    
    if args.all:
        test_all_images()
    elif args.image:
        test_single_image(args.image, save_json=not args.no_save)
    else:
        # Default: test the smallest image
        tests_dir = Path(__file__).parent
        image_files = list(tests_dir.glob("*.png"))
        
        if image_files:
            # Sort by size to test the smallest first (faster)
            image_files.sort(key=lambda p: p.stat().st_size)
            print(f"Testing smallest image: {image_files[0].name}")
            test_single_image(str(image_files[0]), save_json=not args.no_save)
        else:
            print("No PNG images found in tests folder")


if __name__ == "__main__":
    main()

