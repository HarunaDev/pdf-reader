
from pathlib import Path
import re

from src.extractor import extract_pdf_pages
from src.normalizer import normalize_question_table
from src.question_parser import (
    attach_mark_scheme,
    parse_mark_scheme_text,
    parse_question_paper_text,
)
from src.validator import validate_records
from src.json_writer import write_extraction_json
from src.excel_writer import save_tables_to_excel
from src.models import (
    ExaminationPaper,
    ExtractionOutput,
    SourceDocument,
)
from src.metadata_extractor import extract_document_metadata


BASE_DIR = Path(__file__).resolve().parent

QUESTION_PDF_PATH = BASE_DIR / "data" / "exam-question.pdf"
MARK_SCHEME_PDF_PATH = BASE_DIR / "data" / "exam-reading-answer.pdf"

OUTPUT_DIR = BASE_DIR / "output"

QUESTION_TEXT_PATH = OUTPUT_DIR / "question_paper.txt"
MARK_SCHEME_TEXT_PATH = OUTPUT_DIR / "mark_scheme.txt"
EXCEL_OUTPUT_PATH = OUTPUT_DIR / "extracted_tables.xlsx"
JSON_OUTPUT_PATH = OUTPUT_DIR / "questions.json"


def extract_document_text(
    pdf_path: Path,
) -> tuple[str, list[dict[str, object]]]:
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


def create_paper_id(
    subject_code: str | None,
    paper_code: str | None,
    session: str | None,
    year: int | None,
) -> str:
    """Create a readable identifier for an examination paper."""
    parts = [
        subject_code or "unknown-subject",
        paper_code or "unknown-paper",
        session or "unknown-session",
        str(year) if year is not None else "unknown-year",
    ]

    normalized_parts = [
        re.sub(r"[^a-zA-Z0-9]+", "-", part).strip("-").lower()
        for part in parts
    ]

    return "-".join(normalized_parts)


def main() -> None:
    """Extract, validate and export an examination paper."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Verify that both input PDFs exist.
    for pdf_path in (QUESTION_PDF_PATH, MARK_SCHEME_PDF_PATH):
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # 2. Extract the question paper.
    question_text, question_tables = extract_document_text(
        QUESTION_PDF_PATH
    )

    QUESTION_TEXT_PATH.write_text(
        question_text,
        encoding="utf-8",
    )

    # 3. Extract the mark scheme.
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

    # 4. Extract metadata from both PDF cover pages.
    question_document = extract_document_metadata(
        document_text=question_text,
        document_name=QUESTION_PDF_PATH.name,
    )

    mark_scheme_document = extract_document_metadata(
        document_text=mark_scheme_text,
        document_name=MARK_SCHEME_PDF_PATH.name,
    )

    print("\nQuestion paper metadata:")
    print(question_document)

    print("\nMark scheme metadata:")
    print(mark_scheme_document)

    # 5. Export normalized tables to Excel.
    all_tables = question_tables + mark_scheme_tables

    save_tables_to_excel(
        all_tables,
        EXCEL_OUTPUT_PATH,
    )

    print(f"\nTables exported: {len(all_tables)}")
    print(f"Excel saved to: {EXCEL_OUTPUT_PATH}")

    # 6. Register the two physical source documents.
    question_source = SourceDocument(
        document_id="question-paper",
        document_name=question_document.document_name,
        document_type=question_document.document_type,
    )

    mark_scheme_source = SourceDocument(
        document_id="mark-scheme",
        document_name=mark_scheme_document.document_name,
        document_type=mark_scheme_document.document_type,
    )

    source_documents = [
        question_source,
        mark_scheme_source,
    ]

    source_document_ids = {
        source.document_id for source in source_documents
    }

    # 7. Build the shared examination-paper metadata.
    paper_title = question_document.paper_title

    # Keep the title separate from the session and year.
    if (
        question_document.paper_number is not None
        and question_document.paper_type != "Unknown"
    ):
        paper_title = (
            f"Paper {question_document.paper_number} "
            f"{question_document.paper_type}"
        )

    paper = ExaminationPaper(
        paper_id=create_paper_id(
            subject_code=question_document.subject_code,
            paper_code=question_document.paper_code,
            session=question_document.examination_session,
            year=question_document.examination_year,
        ),
        subject=question_document.subject,
        subject_code=question_document.subject_code,
        paper_code=question_document.paper_code,
        paper_number=question_document.paper_number,
        paper_title=paper_title,
        paper_type=question_document.paper_type,
        examination_session=question_document.examination_session,
        examination_year=question_document.examination_year,
        qualification=question_document.qualification,
    )

    # 8. Parse individual questions.
    question_records = parse_question_paper_text(
        text=question_text,
        document=question_document,
        source_document_id=question_source.document_id,
    )

    print(f"\nQuestions parsed: {len(question_records)}")

    # 9. Parse and attach the mark-scheme content.
    mark_scheme_entries = parse_mark_scheme_text(
        mark_scheme_text
    )

    records = attach_mark_scheme(
        records=question_records,
        mark_scheme=mark_scheme_entries,
        mark_scheme_document=mark_scheme_document,
        mark_scheme_document_id=mark_scheme_source.document_id,
    )

    # 10. Validate individual questions.
    valid_records, review_records = validate_records(
        records=records,
        source_document_ids=source_document_ids,
    )

    # 11. Assemble the document-level export.
    extraction_output = ExtractionOutput(
        paper=paper,
        source_documents=source_documents,
        valid_records=valid_records,
        review_records=review_records,
    )

    # 12. Serialize the complete structure to JSON.
    write_extraction_json(
        output=extraction_output,
        output_path=JSON_OUTPUT_PATH,
    )

    print(f"\nRecords parsed: {len(records)}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Records requiring review: {len(review_records)}")
    print(f"JSON saved to: {JSON_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
