
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from .subject_discovery import Subject

REQUEST_TIMEOUT = 20
CAMBRIDGE_HOST = "www.cambridgeinternational.org"

# SESSION_PATTERN = re.compile(
#     r"\b(january|february|march|april|may|june|july|august|"
#     r"september|october|november|december)\b",
#     re.IGNORECASE,
# )
MONTH_PATTERN = (
    r"january|february|march|april|may|june|july|august|"
    r"september|october|november|december"
)

SESSION_PATTERN = re.compile(
    rf"\b({MONTH_PATTERN})(?:\s*/\s*({MONTH_PATTERN}))?\b",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
PAPER_PATTERN = re.compile(r"\bpaper\s*([0-9]+(?:/[0-9]+)*)\b", re.IGNORECASE)

IGNORED_SECTION_PATTERN = re.compile(
    r"digital exams?|examiner reports?",
    re.IGNORECASE,
)
SECTION_PATTERN = re.compile(
    r"past papers?|specimen papers?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PDFResource:
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class ExamEntry:
    subject_name: str
    syllabus_code: str
    collection_type: str
    title: str
    session: str | None
    year: int | None
    paper: str | None
    question_paper: PDFResource | None
    mark_scheme: PDFResource | None
    reading_passage: PDFResource | None


def fetch_html(url: str) -> str:
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": "pdf-scanner/1.0 (educational resource discovery)"
        },
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "html" not in content_type:
        raise ValueError(f"Expected an HTML page at {url}")

    return response.text


def is_cambridge_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == CAMBRIDGE_HOST
    )


def canonical_url(base_url: str, href: str) -> str:
    return urldefrag(urljoin(base_url, href)).url


def is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def link_title(link: Tag, url: str) -> str:
    title = link.get_text(" ", strip=True)
    if title:
        return title

    return Path(urlparse(url).path).name or url


def get_section_type(title: str) -> str | None:
    normalized = " ".join(title.split()).casefold()

    if "specimen" in normalized and "paper" in normalized:
        return "specimen_paper"

    if "past paper" in normalized:
        return "past_paper"

    return None


def classify_pdf(title: str, url: str) -> str:
    text = f"{title} {url}".casefold().replace("_", " ")

    if "examiner report" in text or "examiner-report" in text:
        return "examiner_report"

    if "mark scheme" in text or "mark-scheme" in text:
        return "mark_scheme"

    if "question paper" in text or "question-paper" in text:
        return "question_paper"

    if any(word in text for word in ("insert", "reading passage", "reading text")):
        return "reading_passage"

    return "other"


def extract_pdf_links(container: Tag, page_url: str) -> list[tuple[str, str, str]]:
    """Return (visible title, absolute URL, classification) for PDF links."""
    results: list[tuple[str, str, str]] = []
    seen_urls: set[str] = set()

    for link in container.find_all("a", href=True):
        href = str(link["href"]).strip()
        if not href or href.startswith(("mailto:", "javascript:", "tel:")):
            continue

        url = canonical_url(page_url, href)

        if not is_cambridge_url(url) or not is_pdf_url(url):
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)
        title = link_title(link, url)
        results.append((title, url, classify_pdf(title, url)))

    return results


def _looks_like_entry(container: Tag, page_url: str) -> bool:
    pdf_links = extract_pdf_links(container, page_url)
    if not pdf_links:
        return False

    text = container.get_text(" ", strip=True)
    return bool(YEAR_PATTERN.search(text) or SESSION_PATTERN.search(text))


def find_entry_container(link: Tag, page_url: str) -> Tag | None:
    """
    Find the smallest ancestor that looks like one dated exam entry.

    This is intentionally conservative: it avoids selecting an ancestor
    containing a large list of unrelated PDF links.
    """
    # current = link.parent

    # while isinstance(current, Tag) and current.name not in {"body", "html"}:
    #     if _looks_like_entry(current, page_url):
    #         pdf_count = len(extract_pdf_links(current, page_url))

    #         if pdf_count <= 6:
    #             return current

    #     current = current.parent

    # return None
    current = link.parent
    list_item: Tag | None = None

    while isinstance(current, Tag) and current.name not in {"body", "html"}:
        if current.name == "li":
            list_item = current
            break

        current = current.parent

    if list_item is not None:
        links = extract_pdf_links(list_item, page_url)

        if any(item[2] == "question_paper" for item in links):
            return list_item

    return None


def extract_session(text: str) -> str | None:
    match = SESSION_PATTERN.search(text)
    return match.group(0).title() if match else None


def extract_year(text: str) -> int | None:
    match = YEAR_PATTERN.search(text)
    return int(match.group(1)) if match else None


def extract_paper(text: str) -> str | None:
    match = PAPER_PATTERN.search(text)
    return match.group(1) if match else None


def _make_pdf_resource(
    item: tuple[str, str, str],
) -> PDFResource:
    title, url, _resource_type = item
    return PDFResource(title=title, url=url)


# def build_exam_entry(
#     container: Tag,
#     subject: Subject,
#     page_url: str,
#     collection_type: str,
# ) -> ExamEntry | None:
#     pdf_links = extract_pdf_links(container, page_url)
#     if not pdf_links:
#         return None

#     # Examiner reports are never included in the exam entry.
#     pdf_links = [
#         item for item in pdf_links
#         if item[2] != "examiner_report"
#     ]

#     if not pdf_links:
#         return None

#     text = " ".join(container.get_text(" ", strip=True).split())

#     # Prefer explicit link labels. If the page only identifies the
#     # question paper and leaves the supporting files unlabeled, assign
#     # the remaining PDFs in document order as requested.
#     question_paper = next(
#         (item for item in pdf_links if item[2] == "question_paper"),
#         None,
#     )

#     remaining = [
#         item for item in pdf_links
#         if item is not question_paper
#     ]

#     mark_scheme = next(
#         (item for item in remaining if item[2] == "mark_scheme"),
#         None,
#     )
#     reading_passage = next(
#         (item for item in remaining if item[2] == "reading_passage"),
#         None,
#     )

#     if question_paper is not None:
#         remaining = [item for item in remaining if item is not mark_scheme]
#         remaining = [item for item in remaining if item is not reading_passage]

#         if mark_scheme is None and remaining:
#             mark_scheme = remaining.pop(0)

#         if reading_passage is None and remaining:
#             reading_passage = remaining.pop(0)

#     # If there is no explicitly labeled question paper, don't guess
#     # which PDF is the question paper. Keep the entry out of the output
#     # so it can be inspected rather than silently misclassified.
#     if question_paper is None:
#         return None

#     title = text[:180] if text else question_paper[0]

#     return ExamEntry(
#         subject_name=subject.name,
#         syllabus_code=subject.syllabus_code,
#         collection_type=collection_type,
#         title=title,
#         session=extract_session(text),
#         year=extract_year(text),
#         paper=extract_paper(text),
#         question_paper=_make_pdf_resource(question_paper),
#         mark_scheme=(
#             _make_pdf_resource(mark_scheme)
#             if mark_scheme is not None
#             else None
#         ),
#         reading_passage=(
#             _make_pdf_resource(reading_passage)
#             if reading_passage is not None
#             else None
#         ),
#     )

def build_exam_entry(
    container: Tag,
    subject: Subject,
    page_url: str,
    collection_type: str,
) -> ExamEntry | None:
    pdf_links = extract_pdf_links(container, page_url)

    # Never include examiner reports as exam materials.
    pdf_links = [
        item for item in pdf_links
        if item[2] != "examiner_report"
    ]

    question_papers = [
        item for item in pdf_links
        if item[2] == "question_paper"
    ]

    if not question_papers:
        return None

    # Each entry should correspond to one question paper.
    question_paper = question_papers[0]
    question_paper_text = f"{question_paper[0]} {question_paper[1]}"

    year = extract_year(question_paper_text)
    session = extract_session(question_paper_text)
    paper = extract_paper(question_paper_text)

    def matches_paper(item: tuple[str, str, str]) -> bool:
        text = f"{item[0]} {item[1]}"

        item_year = extract_year(text)
        item_session = extract_session(text)
        item_paper = extract_paper(text)

        return (
            item_year == year
            and (
                item_session is None
                or session is None
                or item_session.casefold() == session.casefold()
            )
            and (
                item_paper is None
                or paper is None
                or item_paper == paper
            )
        )

    related_links = [
        item for item in pdf_links
        if item is not question_paper and matches_paper(item)
    ]

    mark_scheme = next(
        (item for item in related_links if item[2] == "mark_scheme"),
        None,
    )

    reading_passage = next(
        (item for item in related_links if item[2] == "reading_passage"),
        None,
    )

    # Use the source order only for unlabeled supporting PDFs.
    unclassified = [
        item for item in related_links
        if item[2] == "other"
    ]

    if mark_scheme is None and unclassified:
        mark_scheme = unclassified.pop(0)

    if reading_passage is None and unclassified:
        reading_passage = unclassified.pop(0)

    return ExamEntry(
        subject_name=subject.name,
        syllabus_code=subject.syllabus_code,
        collection_type=collection_type,
        title=question_paper[0],
        session=session,
        year=year,
        paper=paper,
        question_paper=PDFResource(
            title=question_paper[0],
            url=question_paper[1],
        ),
        mark_scheme=(
            PDFResource(title=mark_scheme[0], url=mark_scheme[1])
            if mark_scheme is not None
            else None
        ),
        reading_passage=(
            PDFResource(
                title=reading_passage[0],
                url=reading_passage[1],
            )
            if reading_passage is not None
            else None
        ),
    )



def extract_section_entries(
    soup: BeautifulSoup,
    subject: Subject,
    page_url: str,
) -> list[ExamEntry]:
    """
    Find Past papers and Specimen papers sections and process their
    dated entry containers. Digital exams and examiner reports are skipped.
    """
    entries: list[ExamEntry] = []
    seen_containers: set[int] = set()

    section_headings = soup.find_all(
        lambda tag: (
            isinstance(tag, Tag)
            and tag.name in {"h1", "h2", "h3", "h4", "h5"}
            and get_section_type(tag.get_text(" ", strip=True)) is not None
        )
    )

    for heading in section_headings:
        heading_text = heading.get_text(" ", strip=True)

        if IGNORED_SECTION_PATTERN.search(heading_text):
            continue

        collection_type = get_section_type(heading_text)
        if collection_type is None:
            continue

        # Search only the section's following content, stopping at the
        # next heading of the same or higher level.
        heading_level = int(heading.name[1])
        section_links: list[Tag] = []

        for element in heading.find_all_next():
            if element.name in {"h1", "h2", "h3", "h4", "h5"}:
                if int(element.name[1]) <= heading_level:
                    break

                heading_text_next = element.get_text(" ", strip=True)
                if IGNORED_SECTION_PATTERN.search(heading_text_next):
                    break

            if element.name != "a" or not element.get("href"):
                continue

            url = canonical_url(page_url, str(element["href"]))
            if is_cambridge_url(url) and is_pdf_url(url):
                section_links.append(element)

        for link in section_links:
            container = find_entry_container(link, page_url)
            if container is None:
                continue

            identity = id(container)
            if identity in seen_containers:
                continue

            seen_containers.add(identity)

            entry = build_exam_entry(
                container=container,
                subject=subject,
                page_url=page_url,
                collection_type=collection_type,
            )
            if entry is not None:
                entries.append(entry)

    return entries


def discover_resources(subject: Subject) -> list[ExamEntry]:
    """
    Discover past-paper and specimen-paper entries from the subject's
    own pages. Do not crawl arbitrary links or unrelated support pages.
    """
    subject_url = subject.url.rstrip("/") + "/"
    past_papers_url = urljoin(subject_url, "past-papers/")

    pages = [
        (subject_url, None),
        (past_papers_url, "past_papers"),
    ]

    discovered: dict[tuple[str, str, str | None], ExamEntry] = {}

    for page_url, _expected_type in pages:
        print(f"Inspecting page: {page_url}")

        try:
            html = fetch_html(page_url)
        except (requests.RequestException, ValueError) as exc:
            print(f"  Skipping page: {exc}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        entries = extract_section_entries(soup, subject, page_url)

        # Some subject pages may link to PDF resources directly. We do
        # not treat those standalone PDFs as complete exam entries.
        print(f"  Exam entries found: {len(entries)}")

        for entry in entries:
            key = (
                entry.collection_type,
                entry.title,
                entry.question_paper.url if entry.question_paper else None,
            )
            discovered.setdefault(key, entry)

    return sorted(
        discovered.values(),
        key=lambda entry: (
            entry.year or 0,
            entry.session or "",
            entry.title.casefold(),
        ),
        reverse=True,
    )


def save_resources(resources: list[ExamEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            [asdict(resource) for resource in resources],
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")
