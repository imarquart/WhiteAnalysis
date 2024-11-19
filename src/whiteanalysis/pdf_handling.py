from io import BytesIO

from pydantic import BaseModel
from pypdf import PdfReader
from unstructured.partition.pdf import partition_pdf


class PDFDocument(BaseModel):
    filename: str
    page: int
    text: str


def get_content_from_pdf(file: BytesIO, filename: str) -> list[PDFDocument]:
    """Loads a PDF file into a list of Document objects.

    Args:
        file: File object.
        filename: Name of the file.

    Returns:
        List of Document objects.
    """
    pdf_reader = PdfReader(file)
    text = ""
    pages: list[PDFDocument] = []
    for i, page in enumerate(pdf_reader.pages):
        text = page.extract_text()
        doc = PDFDocument(filename=filename, page=i, text=text)
        pages.append(doc)
    return pages


def get_content_from_unstructured(filename: str) -> list[PDFDocument]:
    """Loads a PDF file into a list of Document objects.

    Args:
        filename: Name of the file.

    Returns:
        List of Document objects.
    """
    elements = partition_pdf(filename)
    # Using tiktoken, cut into pages of 2048 tokens
    buffer = ""
    pages = []
    for element in elements:
        if len(buffer) + len(str(element)) > 2048:
            pages.append(buffer)
            buffer = ""
        buffer += str(element)
    if buffer:
        pages.append(buffer)
    documents = []
    for i, page in enumerate(pages):
        doc = PDFDocument(filename=filename, page=i, text=page)
        documents.append(doc)
    return documents
