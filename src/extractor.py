from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass(slots=True)
class ExtractedPage:
    page_number: int
    text: str
    tables: list[list[list[str | None]]]


def extract_pdf_pages(pdf_path: Path) -> list[ExtractedPage]:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    extracted_pages: list[ExtractedPage] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            extracted_pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=page.extract_text(x_tolerance=1, y_tolerance=3) or "",
                    tables=page.extract_tables() or [],
                )
            )

    return extracted_pages
