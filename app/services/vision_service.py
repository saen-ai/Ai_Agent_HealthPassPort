"""OpenAI Vision API service for image-based extraction."""

import base64
import json
from pathlib import Path
from typing import List, Optional
from openai import OpenAI

from app.config import settings
from app.core.logging import logger


class VisionService:
    """Service for extracting data from images using GPT-4o Vision."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    @staticmethod
    def image_to_base64(image_path: str) -> str:
        """Convert image file to base64 string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def extract_from_image(self, image_path: str) -> dict:
        """
        Extract lab report data from a single image using GPT-4o Vision.
        Returns extracted data as a dictionary.
        """
        try:
            base64_image = self.image_to_base64(image_path)
            
            prompt = """You are a medical lab report data extractor.

Analyze this lab report image and extract ALL information you can find.

Return a JSON object with:
{
    "lab_name": "Name of the laboratory (if visible)",
    "report_date": "Date of the report in YYYY-MM-DD format (if visible)",
    "patient_info": {
        "name": "Patient name (if visible)",
        "dob": "Date of birth (if visible)",
        "id": "Patient ID (if visible)"
    },
    "report_type": "Type of test - one of: CBC, LIPID, METABOLIC, THYROID, LIVER, KIDNEY, VITAMIN, HORMONE, OTHER",
    "biomarkers": [
        {
            "name": "Test/biomarker name exactly as shown",
            "value": numeric_value_only,
            "unit": "Unit of measurement",
            "reference_min": numeric_min_or_null,
            "reference_max": numeric_max_or_null,
            "flag": "HIGH or LOW or null based on reference range"
        }
    ]
}

Important:
- Extract EVERY biomarker/test result you can see
- Use the exact test name as shown in the report
- For value, extract only the numeric part
- If reference range is shown as "X - Y", extract min=X, max=Y
- Flag as HIGH if value > reference_max, LOW if value < reference_min
- Return ONLY valid JSON, no markdown or explanation"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON from response
            # Clean up if response has markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            result = result.strip()
            
            return json.loads(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Vision API response as JSON: {e}")
            return {"error": "Failed to parse response", "raw": result if 'result' in locals() else None}
        except Exception as e:
            logger.error(f"Error extracting from image with Vision API: {e}")
            return {"error": str(e)}
    
    def extract_from_multiple_images(self, image_paths: List[str]) -> dict:
        """
        Extract data from multiple images and merge results.
        Later pages can override/supplement earlier pages.
        """
        merged_result = {
            "lab_name": None,
            "report_date": None,
            "patient_info": {},
            "report_type": "OTHER",
            "biomarkers": []
        }
        
        for image_path in image_paths:
            logger.info(f"Extracting from: {Path(image_path).name}")
            result = self.extract_from_image(image_path)
            
            if "error" in result:
                logger.warning(f"Error extracting from {image_path}: {result['error']}")
                continue
            
            # Merge results
            if result.get("lab_name"):
                merged_result["lab_name"] = result["lab_name"]
            
            if result.get("report_date"):
                merged_result["report_date"] = result["report_date"]
            
            if result.get("patient_info"):
                merged_result["patient_info"].update(result["patient_info"])
            
            if result.get("report_type") and result["report_type"] != "OTHER":
                merged_result["report_type"] = result["report_type"]
            
            if result.get("biomarkers"):
                merged_result["biomarkers"].extend(result["biomarkers"])
        
        # Remove duplicate biomarkers (keep last occurrence)
        seen = {}
        unique_biomarkers = []
        for bio in merged_result["biomarkers"]:
            name = bio.get("name", "").lower()
            seen[name] = bio
        unique_biomarkers = list(seen.values())
        merged_result["biomarkers"] = unique_biomarkers
        
        return merged_result

