
import sys
from pathlib import Path

# Allow this script to run directly from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapper.subject_discovery import (  # noqa: E402
    discover_subjects,
    save_subjects,
)


def main() -> None:
    output_path = PROJECT_ROOT / "data" / "manifests" / "subjects.json"

    print("Discovering Cambridge IGCSE subjects...")

    subjects = discover_subjects()
    save_subjects(subjects, output_path)

    print(f"Subjects discovered: {len(subjects)}")
    print(f"Saved to: {output_path.relative_to(PROJECT_ROOT)}")

    print("\nFirst 10 subjects:")

    for subject in subjects[:10]:
        print(
            f"- {subject.name} "
            f"({subject.syllabus_code})"
        )
        print(f"  {subject.url}")


if __name__ == "__main__":
    main()
