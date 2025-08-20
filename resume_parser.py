# resume_parser.py (Unchanged, validated for integration)
import fitz  # type: ignore # PyMuPDF

def extract_text_from_pdf(path):
    try:
        text = ""
        doc = fitz.open(path)
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")