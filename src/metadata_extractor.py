
import re
from pathlib import Path

from src.models import DocumentMetadata, DocumentType, PaperType


PAGE_MARKER_PATTERN = re.compile(r"^--- Page \d+ ---\s*$", re.MULTILINE)

SESSION_PATTERN = re.compile(
    r"\b(May\s*/\s*June|October\s*/\s*November|"
    r"February\s*/\s*March|March|June|November)\s+(20\d{2})\b",
    re.IGNORECASE,
)

PAPER_CODE_PATTERN = re.compile(r"\b(\d{4}/\d{2})\b")

PAPER_TITLE_PATTERN = re.compile(
    r"\bPaper\s+(\d+)\s*[-:–]?\s*([A-Za-z][A-Za-z &/,-]*)?",
    re.IGNORECASE,
)

QUALIFICATION_PATTERN = re.compile(
    r"\b(Cambridge\s+IGCSE|Cambridge\s+O\s+Level|"
    r"Cambridge\s+International\s+AS\s*&?\s*A\s+Level|"
    r"International\s+GCSE|IGCSE)\b",
    re.IGNORECASE,
)


def _get_cover_text(document_text: str) -> str:
    """Return the extracted text for physical PDF page one."""
    pages = PAGE_MARKER_PATTERN.split(document_text, maxsplit=1)

    if len(pages) < 2:
        return document_text

    cover_and_remaining = pages[1]
    next_page = re.search(
        r"(?m)^--- Page \d+ ---\s*$",
        cover_and_remaining,
    )

    if next_page:
        return cover_and_remaining[:next_page.start()]

    return cover_and_remaining


def _normalize_session(value: str) -> str:
    """Normalize session names, e.g. May / June to May/June."""
    return re.sub(r"\s*/\s*", "/", value).strip()


def _classify_paper_type(title: str) -> PaperType:
    """Classify a paper title into a supported paper-type option."""
    normalized = title.lower()

    if "reading" in normalized and "writing" in normalized:
        return "Reading and Writing"

    if "reading" in normalized:
        return "Reading"

    if "writing" in normalized or "directed writing" in normalized:
        return "Writing"

    if "listening" in normalized:
        return "Listening"

    if "speaking" in normalized:
        return "Speaking"

    if not title:
        return "Unknown"

    return "Other"


def _extract_subject(cover_text: str) -> str | None:
    """Infer the subject from meaningful cover-page text."""
    lines = cover_text.splitlines()

    for line in lines[:25]:
        candidate = re.sub(r"\s+", " ", line).strip()

        if not candidate:
            continue

        candidate = QUALIFICATION_PATTERN.sub("", candidate)
        candidate = PAPER_CODE_PATTERN.sub("", candidate)
        candidate = SESSION_PATTERN.sub("", candidate)
        candidate = re.sub(r"\b20\d{2}\b", "", candidate)
        candidate = re.sub(
            r"\bPaper\s+\d+.*$",
            "",
            candidate,
            flags=re.IGNORECASE,
        )
        candidate = re.sub(
            r"\bMark\s+Scheme\b",
            "",
            candidate,
            flags=re.IGNORECASE,
        )
        candidate = re.sub(r"^[\s:–—-]+|[\s:–—-]+$", "", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()

        if not candidate:
            continue

        if re.search(
            r"\b(examination|question paper|confidential|"
            r"turn over|instructions|copyright|published)\b",
            candidate,
            re.IGNORECASE,
        ):
            continue

        if len(candidate) > 100:
            continue

        if not re.search(r"[A-Za-z]", candidate):
            continue

        return candidate

    return None


def extract_document_metadata(
    document_text: str,
    document_name: str,
) -> DocumentMetadata:
    """Extract examination metadata from the first page of a PDF."""
    cover_text = _get_cover_text(document_text)
    normalized_cover = re.sub(r"\s+", " ", cover_text)

    session_match = SESSION_PATTERN.search(normalized_cover)
    paper_code_match = PAPER_CODE_PATTERN.search(normalized_cover)
    paper_title_match = PAPER_TITLE_PATTERN.search(normalized_cover)
    qualification_match = QUALIFICATION_PATTERN.search(normalized_cover)

    examination_session = None
    examination_year = None

    if session_match:
        examination_session = _normalize_session(session_match.group(1))
        examination_year = int(session_match.group(2))

    paper_number = None
    paper_title = None
    paper_type: PaperType = "Unknown"

    if paper_title_match:
        paper_number = int(paper_title_match.group(1))
        title_suffix = (paper_title_match.group(2) or "").strip(" -:–,")

        paper_title = f"Paper {paper_number}"
        if title_suffix:
            paper_title = f"{paper_title} {title_suffix}"

        paper_type = _classify_paper_type(title_suffix)

    document_type: DocumentType = "question_paper"

    if re.search(r"\bmark\s+scheme\b", cover_text, re.IGNORECASE):
        document_type = "mark_scheme"

    paper_code = (
        paper_code_match.group(1)
        if paper_code_match
        else None
    )

    return DocumentMetadata(
        document_name=Path(document_name).name,
        document_type=document_type,
        subject=_extract_subject(cover_text),
        subject_code=paper_code.split("/")[0] if paper_code else None,
        paper_code=paper_code,
        paper_number=paper_number,
        paper_title=paper_title,
        paper_type=paper_type,
        examination_session=examination_session,
        examination_year=examination_year,
        qualification=(
            qualification_match.group(1)
            if qualification_match
            else None
        ),
    )
