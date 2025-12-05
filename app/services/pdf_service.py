"""PDF processing service using PyMuPDF and pdfplumber."""

import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Tuple, List, Optional

from app.core.logging import logger


class PDFService:
    """Service for PDF text and table extraction."""
    
    @staticmethod
    def check_encryption(pdf_path: str) -> bool:
        """Check if PDF is encrypted/password-protected."""
        try:
            doc = fitz.open(pdf_path)
            is_encrypted = doc.is_encrypted
            doc.close()
            return is_encrypted
        except Exception as e:
            logger.error(f"Error checking PDF encryption: {e}")
            return False
    
    @staticmethod
    def decrypt_pdf(pdf_path: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Try to decrypt PDF with given password.
        Returns (success, error_message).
        """
        try:
            doc = fitz.open(pdf_path)
            
            if not doc.is_encrypted:
                doc.close()
                return True, None
            
            if doc.authenticate(password):
                doc.close()
                return True, None
            else:
                doc.close()
                return False, "Incorrect password"
                
        except Exception as e:
            logger.error(f"Error decrypting PDF: {e}")
            return False, str(e)
    
    @staticmethod
    def extract_text(pdf_path: str, password: Optional[str] = None) -> str:
        """
        Extract text from PDF using PyMuPDF.
        Returns extracted text or empty string if extraction fails.
        """
        try:
            doc = fitz.open(pdf_path)
            
            # Decrypt if needed
            if doc.is_encrypted and password:
                if not doc.authenticate(password):
                    doc.close()
                    return ""
            
            text = ""
            for page in doc:
                text += page.get_text()
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    @staticmethod
    def extract_tables(pdf_path: str, password: Optional[str] = None) -> List[List[List[str]]]:
        """
        Extract tables from PDF using pdfplumber.
        Returns list of tables, where each table is a list of rows.
        """
        tables = []
        try:
            with pdfplumber.open(pdf_path, password=password) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
        
        return tables
    
    @staticmethod
    def has_images_or_scanned(pdf_path: str, password: Optional[str] = None) -> bool:
        """
        Check if PDF contains images or appears to be scanned.
        Returns True if text extraction yields very little text but pages exist.
        """
        try:
            doc = fitz.open(pdf_path)
            
            if doc.is_encrypted and password:
                doc.authenticate(password)
            
            page_count = doc.page_count
            
            # Check text content
            total_text = ""
            total_images = 0
            
            for page in doc:
                total_text += page.get_text()
                # Count images on page
                image_list = page.get_images()
                total_images += len(image_list)
            
            doc.close()
            
            # If we have pages but very little text, likely scanned
            text_per_page = len(total_text.strip()) / max(page_count, 1)
            
            # Heuristic: if less than 100 chars per page on average, likely image-based
            # Or if there are more images than text blocks
            if text_per_page < 100 or total_images > 0:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for images in PDF: {e}")
            return True  # Assume needs vision if we can't determine
    
    @staticmethod
    def pdf_to_images(pdf_path: str, output_dir: str, password: Optional[str] = None) -> List[str]:
        """
        Convert PDF pages to PNG images for Vision API.
        Returns list of image file paths.
        """
        image_paths = []
        
        try:
            doc = fitz.open(pdf_path)
            
            if doc.is_encrypted and password:
                doc.authenticate(password)
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            for page_num, page in enumerate(doc):
                # High resolution for better OCR
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
                pix = page.get_pixmap(matrix=mat)
                
                image_path = str(output_path / f"page_{page_num + 1}.png")
                pix.save(image_path)
                image_paths.append(image_path)
                
                logger.info(f"Saved page {page_num + 1} to {image_path}")
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
        
        return image_paths
    
    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        """Get number of pages in PDF."""
        try:
            doc = fitz.open(pdf_path)
            count = doc.page_count
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return 0

