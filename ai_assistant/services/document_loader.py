from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader


def load_pdf(file_path):
    pdf_path = Path(file_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    loader = PyPDFLoader(str(pdf_path))
    documents = loader.load()

    return documents