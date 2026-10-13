
from pathlib import Path

import pdfplumber
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "data" / "exam-reading-answer.pdf"

OUTPUT_DIR = BASE_DIR / "output"
TEXT_OUTPUT_PATH = OUTPUT_DIR / "extracted_text_2.txt"
EXCEL_OUTPUT_PATH = OUTPUT_DIR / "extracted_tables.xlsx"


def extract_pdf(pdf_path: Path) -> tuple[str, list[dict[str, object]]]:
    """Extract text from every page of a PDF."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    page_texts: list[str] = []
    extracted_tables: list[dict[str, object]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            page_texts.append(
                f"--- Page {page_number} ---\n{text}"
            )

        # Extract tables from the same page.
            tables = page.extract_tables()

            for table_number, table in enumerate(tables, start=1):
                if not table:
                    continue

                # Convert the table rows into a DataFrame.
                df = pd.DataFrame(table)

                # Remove completely empty rows and columns.
                df = df.replace(r"^\s*$", pd.NA, regex=True)
                df = df.dropna(axis=0, how="all")
                df = df.dropna(axis=1, how="all")

                if df.empty:
                    continue

                extracted_tables.append(
                    {
                        "page": page_number,
                        "table_number": table_number,
                        "dataframe": df,
                    }
                )

    return "\n\n".join(page_texts), extracted_tables


def save_tables_to_excel(
    tables: list[dict[str, object]],
    output_path: Path,
) -> None:
    """Save each extracted table to its own Excel worksheet."""

    if not tables:
        print("No tables were detected in the PDF.")
        return

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for table in tables:
            page_number = int(table["page"])
            table_number = int(table["table_number"])
            df = table["dataframe"]

            if not isinstance(df, pd.DataFrame):
                continue

            sheet_name = f"Page{page_number}_Table{table_number}"
            df.to_excel(
                writer,
                sheet_name=sheet_name[:31],
                index=False,
                header=False,
            )

    print(f"Extracted {len(tables)} table(s).")
    print(f"Excel file saved to: {output_path}")

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extracted_text, tables = extract_pdf(PDF_PATH)

    # Save the regular page text.
    TEXT_OUTPUT_PATH.write_text(
        extracted_text,
        encoding="utf-8",
    )

    print(f"PDF processed: {PDF_PATH.name}")
    print(f"Text saved to: {TEXT_OUTPUT_PATH}")

    # Save tables separately in Excel.
    save_tables_to_excel(tables, EXCEL_OUTPUT_PATH)



if __name__ == "__main__":
    main()
