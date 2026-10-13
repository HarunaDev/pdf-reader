from pathlib import Path
from src.extractor import extract_pdf
from src.excel_writer import save_tables_to_excel

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "data" / "exam-reading-answer.pdf"

OUTPUT_DIR = BASE_DIR / "output"
TEXT_OUTPUT_PATH = OUTPUT_DIR / "extracted_text_2.txt"
EXCEL_OUTPUT_PATH = OUTPUT_DIR / "extracted_tables.xlsx"

def main() -> None:
    """Coordinate the PDF extraction workflow."""


    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Extract text and normalized tables.
    extracted_text, tables = extract_pdf(PDF_PATH)

    # Save the regular page text.
    TEXT_OUTPUT_PATH.write_text(
        extracted_text,
        encoding="utf-8",
    )

    # Save tables separately in Excel.
    save_tables_to_excel(tables, EXCEL_OUTPUT_PATH)



if __name__ == "__main__":
    main()
