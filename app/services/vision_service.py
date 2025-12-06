"""OpenAI Vision API service for image-based extraction."""

import base64
import json
import re
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
    
    @staticmethod
    def get_mime_type(image_path: str) -> str:
        """Get MIME type based on file extension."""
        ext = Path(image_path).suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(ext, "image/png")
    
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[dict]:
        """
        Extract JSON object from text that may contain markdown or other content.
        Uses multiple strategies to find valid JSON.
        """
        if not text:
            return None
        
        # Strategy 1: Try parsing the text directly
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Remove markdown code blocks
        # Handle ```json ... ``` and ``` ... ```
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
            r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Find JSON object by looking for { ... }
        # Find the outermost curly braces
        start_idx = text.find('{')
        if start_idx != -1:
            # Count braces to find matching end
            depth = 0
            end_idx = start_idx
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            
            if end_idx > start_idx:
                try:
                    json_str = text[start_idx:end_idx + 1]
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        return None
    
    def extract_from_image(self, image_path: str) -> dict:
        """
        Extract lab report data from a single image using GPT-4o Vision.
        Returns extracted data as a dictionary.
        """
        try:
            base64_image = self.image_to_base64(image_path)
            mime_type = self.get_mime_type(image_path)
            
            prompt = """You are a medical lab report data extractor.

Analyze this lab report image and extract ALL information you can find.

Return a JSON object with:
{
    "lab_name": "Name of the laboratory (if visible)",
    "report_date": "Date of the report in YYYY-MM-DD format (if visible, convert any date format to YYYY-MM-DD)",
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
- For value, extract only the numeric part (as a number, not string)
- If reference range is shown as "X - Y", extract min=X, max=Y
- Flag as HIGH if value > reference_max, LOW if value < reference_min
- Return ONLY valid JSON, no markdown code blocks or explanation
- If you cannot extract a date, set report_date to null"""

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
                                    "url": f"data:{mime_type};base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1,  # Lower temperature for more consistent JSON output
            )
            
            result_text = response.choices[0].message.content
            logger.debug(f"Vision API raw response: {result_text[:500]}...")
            
            # Try to extract JSON from the response
            parsed = self.extract_json_from_text(result_text)
            
            if parsed:
                logger.info(f"Successfully extracted {len(parsed.get('biomarkers', []))} biomarkers from image")
                return parsed
            
            # If parsing failed, log the raw response and return error
            logger.error(f"Failed to extract JSON from Vision API response. Raw: {result_text}")
            return {
                "error": "Failed to parse response",
                "raw": result_text,
            }
            
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
        for bio in merged_result["biomarkers"]:
            name = bio.get("name", "").lower()
            seen[name] = bio
        merged_result["biomarkers"] = list(seen.values())
        
        logger.info(f"Merged {len(merged_result['biomarkers'])} unique biomarkers from {len(image_paths)} images")
        
        return merged_result
