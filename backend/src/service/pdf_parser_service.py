from pypdf import PdfReader

def extract_pdf_markdown(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join([page.extract_text() for page in reader.pages])