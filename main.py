
from pathlib import Path

from src.extractor import extract_pdf_pages
from src.normalizer import normalize_question_table
from src.question_parser import (attach_mark_scheme, parse_mark_scheme_text, parse_question_paper_text)
from src.validator import validate_records
from src.json_writer import write_questions_json
from src.excel_writer import save_tables_to_excel
from src.models import DocumentMetadata
from src.metadata_extractor import extract_document_metadata


BASE_DIR = Path(__file__).resolve().parent

QUESTION_PDF_PATH = BASE_DIR / "data" / "exam-question.pdf"
MARK_SCHEME_PDF_PATH = BASE_DIR / "data" / "exam-reading-answer.pdf"

OUTPUT_DIR = BASE_DIR / "output"

QUESTION_TEXT_PATH = OUTPUT_DIR / "question_paper.txt"
MARK_SCHEME_TEXT_PATH = OUTPUT_DIR / "mark_scheme.txt"
EXCEL_OUTPUT_PATH = OUTPUT_DIR / "extracted_tables.xlsx"
JSON_OUTPUT_PATH = OUTPUT_DIR / "questions.json"


def extract_document_text(pdf_path: Path) -> tuple[str, list[dict[str, object]]]:
    """Extract page text and normalize tables from one PDF."""

    pages = extract_pdf_pages(pdf_path)

    extracted_text = "\n\n".join(
        f"--- Page {page.page_number} ---\n{page.text}"
        for page in pages
    )

    tables: list[dict[str, object]] = []

    for page in pages:
        for table_number, raw_table in enumerate(page.tables, start=1):
            dataframe = normalize_question_table(raw_table)

            tables.append(
                {
                    "page": page.page_number,
                    "table_number": table_number,
                    "document_name": pdf_path.name,
                    "dataframe": dataframe,
                }
            )

    return extracted_text, tables


def main() -> None:
    """Extract both PDFs and export the available structured data."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure both source documents exist before processing.
    for pdf_path in (QUESTION_PDF_PATH, MARK_SCHEME_PDF_PATH):
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Extract the question paper.
    question_text, question_tables = extract_document_text(
        QUESTION_PDF_PATH
    )

    QUESTION_TEXT_PATH.write_text(
        question_text,
        encoding="utf-8",
    )

    # Extract the mark scheme.
    mark_scheme_text, mark_scheme_tables = extract_document_text(
        MARK_SCHEME_PDF_PATH
    )

    MARK_SCHEME_TEXT_PATH.write_text(
        mark_scheme_text,
        encoding="utf-8",
    )

    print(f"Question paper processed: {QUESTION_PDF_PATH.name}")
    print(f"Question text saved to: {QUESTION_TEXT_PATH}")
    print(f"Mark scheme processed: {MARK_SCHEME_PDF_PATH.name}")
    print(f"Mark scheme text saved to: {MARK_SCHEME_TEXT_PATH}")

    question_document = extract_document_metadata(
    document_text=question_text,
    document_name=QUESTION_PDF_PATH.name,
)

    mark_scheme_document = extract_document_metadata(
        document_text=mark_scheme_text,
        document_name=MARK_SCHEME_PDF_PATH.name,
    )

    print("Question paper metadata:")
    print(question_document)

    print("Mark scheme metadata:")
    print(mark_scheme_document)

    # Export extracted tables from both documents.
    all_tables = question_tables + mark_scheme_tables

    save_tables_to_excel(
        all_tables,
        EXCEL_OUTPUT_PATH,
    )

    print(f"Tables exported: {len(all_tables)}")
    print(f"Excel saved to: {EXCEL_OUTPUT_PATH}")

    # Parse tables from each document separately so each record
    # retains the correct source document name.
    question_records = parse_question_paper_text(
        text=question_text,
        document=question_document,
    )

    mark_scheme_entries = parse_mark_scheme_text(mark_scheme_text)

    records = attach_mark_scheme(
        records=question_records,
        mark_scheme=mark_scheme_entries,
        mark_scheme_document=mark_scheme_document,
    )

    # Validate and separate records.
    valid_records, review_records = validate_records(records)

    # Export structured JSON.
    write_questions_json(
        valid_records=valid_records,
        review_records=review_records,
        output_path=JSON_OUTPUT_PATH,
    )

    print(f"Records parsed: {len(records)}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Records requiring review: {len(review_records)}")
    print(f"JSON saved to: {JSON_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
