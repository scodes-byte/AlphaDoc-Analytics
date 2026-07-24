import os
import base64
from typing import Dict, Any, Tuple
from pypdf import PdfReader
from PIL import Image

class DocumentProcessor:
    """
    Multimodal Document Processor: Handles PDF text parsing as well as image file 
    ingestion (PNG, JPG, WEBP), extracting both textual and visual representations 
    for GenAI & Multimodal Vision models.
    """
    SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}

    @staticmethod
    def process_file(file_path: str) -> Dict[str, Any]:
        """
        Ingests a PDF or image file and returns standardized text and visual metadata.
        
        Args:
            file_path (str): Absolute or relative path to the uploaded document/image.
            
        Returns:
            Dict[str, Any]: Extracted text, document_type, image_b64 (if image), and page count.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found at: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in DocumentProcessor.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: {', '.join(DocumentProcessor.SUPPORTED_EXTENSIONS)}")

        if ext == ".pdf":
            text_content, page_count = DocumentProcessor._extract_from_pdf(file_path)
            return {
                "document_type": "pdf",
                "text_content": text_content,
                "page_count": page_count,
                "image_b64": None,
                "file_name": os.path.basename(file_path)
            }
        else:
            image_b64, dimensions = DocumentProcessor._process_image(file_path)
            text_content = f"[Multimodal Visual Document: {os.path.basename(file_path)} | Dimensions: {dimensions[0]}x{dimensions[1]}px]"
            return {
                "document_type": "image",
                "text_content": text_content,
                "page_count": 1,
                "image_b64": image_b64,
                "dimensions": dimensions,
                "file_name": os.path.basename(file_path)
            }

    @staticmethod
    def _extract_from_pdf(pdf_path: str) -> Tuple[str, int]:
        text = ""
        try:
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_idx + 1} ---\n" + page_text
        except Exception as e:
            raise RuntimeError(f"Failed to parse PDF document structure: {str(e)}")

        text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
        return text, page_count

    @staticmethod
    def _process_image(image_path: str) -> Tuple[str, Tuple[int, int]]:
        try:
            with Image.open(image_path) as img:
                dimensions = img.size
                
            with open(image_path, "rb") as image_file:
                image_b64 = base64.b64encode(image_file.read()).decode("utf-8")
                
            return image_b64, dimensions
        except Exception as e:
            raise RuntimeError(f"Failed to process image file: {str(e)}")

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Legacy helper for text extraction backwards compatibility."""
        text, _ = DocumentProcessor._extract_from_pdf(pdf_path)
        return text

if __name__ == "__main__":
    print("Multimodal DocumentProcessor compiled successfully.")
