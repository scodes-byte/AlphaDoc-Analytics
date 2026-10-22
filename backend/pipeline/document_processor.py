import os
import base64
from typing import Dict, Any, Tuple
from pypdf import PdfReader
from PIL import Image

# Maps Pillow's detected format to the MIME type the vision model expects
IMAGE_MIME_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "BMP": "image/bmp"}


class DocumentProcessor:
    """
    Multimodal Document Processor: extracts the text layer from PDFs and base64-encodes
    images (PNG, JPG, WEBP, BMP) so they can be sent to a vision-language model.
    """
    SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}

    @staticmethod
    def process_file(file_path: str) -> Dict[str, Any]:
        """
        Ingests a PDF or image file and returns standardized text and visual metadata.

        Returns:
            Dict[str, Any]: text_content, document_type, page_count, image_b64 and mime_type (images only).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found at: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in DocumentProcessor.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(DocumentProcessor.SUPPORTED_EXTENSIONS))}")

        if ext == ".pdf":
            text_content, page_count = DocumentProcessor._extract_from_pdf(file_path)
            if not text_content.strip():
                raise ValueError("This PDF has no text layer (it is probably a scan). Upload the pages as images instead.")
            return {
                "document_type": "pdf",
                "text_content": text_content,
                "page_count": page_count,
                "image_b64": None,
                "mime_type": "application/pdf",
                "file_name": os.path.basename(file_path),
            }

        image_b64, dimensions, mime_type = DocumentProcessor._process_image(file_path)
        text_content = f"[Image document: {os.path.basename(file_path)} | {dimensions[0]}x{dimensions[1]}px]"
        return {
            "document_type": "image",
            "text_content": text_content,
            "page_count": 1,
            "image_b64": image_b64,
            "mime_type": mime_type,
            "dimensions": dimensions,
            "file_name": os.path.basename(file_path),
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
    def _process_image(image_path: str) -> Tuple[str, Tuple[int, int], str]:
        try:
            with Image.open(image_path) as img:
                img.verify()  # rejects truncated or non-image files renamed to .png
            with Image.open(image_path) as img:
                dimensions = img.size
                mime_type = IMAGE_MIME_TYPES.get(img.format, "image/jpeg")
            with open(image_path, "rb") as image_file:
                image_b64 = base64.b64encode(image_file.read()).decode("utf-8")
            return image_b64, dimensions, mime_type
        except Exception as e:
            raise ValueError(f"Failed to process image file: {str(e)}")
