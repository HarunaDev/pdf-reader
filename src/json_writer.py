
import json
from pathlib import Path

from src.models import ExtractionOutput

def write_extraction_json(
    output: ExtractionOutput,
    output_path: Path,
) -> None:
    """Write the complete examination extraction result to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(
            output.to_dict(),
            json_file,
            indent=2,
            ensure_ascii=False,
        )
        json_file.write("\n")

