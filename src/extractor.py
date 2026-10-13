from pathlib import Path

import pandas as pd
import pdfplumber

from .normalizer import normalize_question_table


def extract_pdf(
    pdf_path: Path,
) -> tuple[str, list[dict[str, object]]]:
    """Extract text and tables from every page of a PDF."""

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    page_texts: list[str] = []
    extracted_tables: list[dict[str, object]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):
            # Extract regular page text.
            text = page.extract_text() or ""
            page_texts.append(f"--- Page {page_number} ---\n{text}")

            # Extract tables from the current page.
            tables = page.extract_tables()

            for table_number, table in enumerate(
                tables,
                start=1,
            ):
                if not table:
                    continue

                # Normalize the extracted table.
                df = normalize_question_table(table)

                if df.empty:
                    continue

                extracted_tables.append(
                    {
                        "page": page_number,
                        "table_number": table_number,
                        "dataframe": df,
                    }
                )

    extracted_text = "\n\n".join(page_texts)

    return extracted_text, extracted_tables
