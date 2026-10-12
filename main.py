
from pathlib import Path

import pdfplumber

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "data" / "exam-reading.pdf"
OUTPUT_PATH = BASE_DIR / "output" / "extracted_text.txt"


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from every page of a PDF."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    pages: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(
                f"--- Page {page_number} ---\n{text}"
            )

    return "\n\n".join(pages)


def main() -> None:
    extracted_text = extract_pdf_text(PDF_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(extracted_text, encoding="utf-8")

    print(f"PDF processed successfully: {PDF_PATH.name}")
    print(f"Extracted text saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
