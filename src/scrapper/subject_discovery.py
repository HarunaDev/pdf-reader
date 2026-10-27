
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


SUBJECTS_URL = (
    "https://www.cambridgeinternational.org/"
    "programmes-and-qualifications/"
    "cambridge-upper-secondary/"
    "cambridge-igcse/subjects/"
)

REQUEST_TIMEOUT = 20

SUBJECT_CODE_PATTERN = re.compile(
    r"(?<!\d)(\d{4})\)?(?:\s+New)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Subject:
    """A subject listed on the Cambridge IGCSE website."""

    name: str
    syllabus_code: str
    url: str
    qualification: str = "Cambridge IGCSE"


def _parse_subject_name_and_code(
    link_text: str,
) -> tuple[str, str] | None:
    """Extract a subject name and four-digit syllabus code."""
    text = re.sub(r"\s+", " ", link_text).strip()

    match = SUBJECT_CODE_PATTERN.search(text)

    if match is None:
        return None

    syllabus_code = match.group(1)
    name = text[:match.start()].rstrip(" -–—(").strip()

    if not name:
        return None

    return name, syllabus_code


def parse_subjects_html(html: str) -> list[Subject]:
    """Parse subject links from the Cambridge IGCSE subjects page."""
    soup = BeautifulSoup(html, "html.parser")
    subjects_by_url: dict[str, Subject] = {}

    for link in soup.find_all("a", href=True):
        parsed = _parse_subject_name_and_code(
            link.get_text(" ", strip=True)
        )

        if parsed is None:
            continue

        name, syllabus_code = parsed
        url = urljoin(SUBJECTS_URL, link["href"].strip())
        parsed_url = urlparse(url)

        # Only accept links to Cambridge's official website.
        if parsed_url.scheme != "https":
            continue

        if parsed_url.hostname != "www.cambridgeinternational.org":
            continue

        # Restrict discovery to individual qualification pages.
        if not parsed_url.path.startswith("/programmes-and-qualifications/cambridge-igcse-"):
            continue

        # Avoid fragments and query parameters in canonical URLs.
        canonical_url = parsed_url._replace(
            query="",
            fragment="",
        ).geturl()

        subjects_by_url.setdefault(
            canonical_url,
            Subject(
                name=name,
                syllabus_code=syllabus_code,
                url=canonical_url,
            ),
        )

    return sorted(
        subjects_by_url.values(),
        key=lambda subject: (
            subject.name.casefold(),
            subject.syllabus_code,
        ),
    )


def discover_subjects() -> list[Subject]:
    """Fetch the official listing and discover available subjects."""
    response = requests.get(
        SUBJECTS_URL,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": (
                "pdf-scanner/1.0 "
                "(educational resource discovery)"
            )
        },
    )
    response.raise_for_status()

    subjects = parse_subjects_html(response.text)

    if not subjects:
        raise ValueError(
            "No subjects were found. The page structure may have changed."
        )

    return subjects


def save_subjects(
    subjects: list[Subject],
    output_path: Path,
) -> None:
    """Save discovered subjects as a JSON manifest."""
    import json

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            [asdict(subject) for subject in subjects],
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")
