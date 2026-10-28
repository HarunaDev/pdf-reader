
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapper.pdf_downloader import download_manifest

MANIFEST_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "resources_0500.json"
)

OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "pdfs"

REPORT_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "downloads_0500.json"
)


def main() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"Resource manifest not found: {MANIFEST_PATH}"
        )

    results = download_manifest(
        manifest_path=MANIFEST_PATH,
        output_directory=OUTPUT_DIRECTORY,
        report_path=REPORT_PATH,
    )

    downloaded = sum(result.status == "downloaded" for result in results)
    skipped = sum(
        result.status == "skipped_existing" for result in results
    )
    reused = sum(
        result.status == "reused_duplicate_url" for result in results
    )
    failed = sum(result.status == "failed" for result in results)

    print("\n" + "=" * 50)
    print("PDF DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"Resources processed: {len(results)}")
    print(f"Downloaded: {downloaded}")
    print(f"Existing files reused: {skipped}")
    print(f"Duplicate URLs reused: {reused}")
    print(f"Failed: {failed}")
    print(f"PDF directory: {OUTPUT_DIRECTORY}")
    print(f"Download report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
