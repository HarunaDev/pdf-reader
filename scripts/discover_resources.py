
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapper.resource_discovery import (
    ExamEntry,
    PDFResource,
    discover_resources,
    save_resources,
)
from src.scrapper.subject_discovery import Subject

SUBJECTS_PATH = PROJECT_ROOT / "data" / "manifests" / "subjects.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "manifests" / "resources_0500.json"


def print_pdf(label: str, resource: object | None) -> None:
    if resource is None:
        print(f"  {label}: Not available")
        return

    print(f"  {label}: {resource.title}")
    print(f"    {resource.url}")


def print_entry(entry: ExamEntry) -> None:
    session_label = entry.session or "Unknown session"
    year_label = str(entry.year) if entry.year is not None else "Unknown year"

    print(f"\n[{entry.collection_type}] {entry.title}")
    print(f"  Session: {session_label} {year_label}")
    print(f"  Paper: {entry.paper or 'Not identified'}")

    print_pdf("Question paper", entry.question_paper)
    print_pdf("Mark scheme", entry.mark_scheme)
    print_pdf("Reading passage", entry.reading_passage)


def main() -> None:
    with SUBJECTS_PATH.open("r", encoding="utf-8") as file:
        subjects_data = json.load(file)

    selected = next(
        (
            item
            for item in subjects_data
            if item["syllabus_code"] == "0500"
        ),
        None,
    )

    if selected is None:
        raise ValueError("Syllabus 0500 was not found in subjects.json")

    subject = Subject(**selected)

    print(
        f"Discovering resources for "
        f"{subject.name} ({subject.syllabus_code})"
    )

    entries = discover_resources(subject)
    save_resources(entries, OUTPUT_PATH)

    print(f"\nExam entries found: {len(entries)}")
    print(f"Saved manifest to: {OUTPUT_PATH}")

    for entry in entries:
        print_entry(entry)


if __name__ == "__main__":
    main()
