from pathlib import Path

import pdfplumber
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "data" / "exam-reading-answer.pdf"

OUTPUT_DIR = BASE_DIR / "output"
TEXT_OUTPUT_PATH = OUTPUT_DIR / "extracted_text_2.txt"
EXCEL_OUTPUT_PATH = OUTPUT_DIR / "extracted_tables.xlsx"

# normalise question table function
def normalize_question_table(
    table: list[list[str | None]],
) -> pd.DataFrame:
    """
    Normalize question-and-answer tables that pdfplumber
    extracts into nine columns instead of three.
    """
    df = pd.DataFrame(table)

    # Replace empty strings and whitespace with missing values.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # Remove completely empty rows.
    df = df.dropna(axis=0, how="all").reset_index(drop=True)

    if df.empty:
        return df

    # Detect the nine-column Question / Answer / Marks layout.
    if df.shape[1] >= 9:
        first_row = df.iloc[0].fillna("").astype(str).str.strip().tolist()

        # The header is usually on the second extracted row.
        header_row_index = next(
            (
                index
                for index, row in enumerate(
                    df.fillna("").astype(str).values.tolist()
                )
                if (
                    "Question" in row
                    and "Answer" in row
                    and "Marks" in row
                )
            ),
            None,
        )

        if header_row_index is not None:
            normalized_rows: list[list[object]] = [
                ["Question", "Answer", "Marks"]
            ]

            # Read actual question rows, skipping header and blank rows.
            for row_index in range(header_row_index + 1, len(df)):
                row = df.iloc[row_index].tolist()

                question_number = row[0] if len(row) > 0 else None
                answer_text = row[3] if len(row) > 3 else None
                marks = row[6] if len(row) > 6 else None

                # Ignore empty rows and repeated header rows.
                question = (
                    str(question_number).strip()
                    if pd.notna(question_number)
                    else ""
                )
                answer = (
                    str(answer_text).strip()
                    if pd.notna(answer_text)
                    else ""
                )
                mark_value = (
                    str(marks).strip()
                    if pd.notna(marks)
                    else ""
                )

                if question == "Question":
                    continue

                if not question and not answer and not mark_value:
                    continue

                normalized_rows.append(
                    [question, answer, mark_value]
                )

            return pd.DataFrame(normalized_rows)

    # Leave tables that do not match this layout unchanged.
    df = df.dropna(axis=1, how="all")
    return df

# extract pdf function
def extract_pdf(pdf_path: Path) -> tuple[str, list[dict[str, object]]]:
    """Extract text and tables from every page of a PDF."""
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

            # Extract tables using the default settings.
            tables = page.extract_tables()

            for table_number, table in enumerate(tables, start=1):
                if not table:
                    continue

                # Print the first eight rows for debugging.
                print(
                    f"\nPage {page_number}, "
                    f"Table {table_number}"
                )

                for row_number, row in enumerate(table[:8], start=1):
                    print(f"Row {row_number}: {row}")

                # use normalize question table function 
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

    return "\n\n".join(page_texts), extracted_tables

# function to save data to excel table 

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
