import os
from pypdf import PdfReader

class DocumentProcessor:
    """
    Handles file-level processing of incoming financial PDF documents, 
    extracting text content from pages and validating structural properties.
    """
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Reads a PDF file from the disk and extracts text page-by-page.
        
        Args:
            pdf_path (str): Absolute or relative path to the PDF file.
            
        Returns:
            str: The raw text content extracted from the document.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Financial PDF not found at: {pdf_path}")
            
        text = ""
        try:
            reader = PdfReader(pdf_path)
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_idx + 1} ---\n" + page_text
        except Exception as e:
            raise RuntimeError(f"Failed to parse PDF document structure: {str(e)}")
            
        # Clean text basic normalization
        text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
        return text

if __name__ == "__main__":
    # Quick visual dry-run testing block
    print("DocumentProcessor class compiled successfully.")
