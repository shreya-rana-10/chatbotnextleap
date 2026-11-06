import json
import re
from pathlib import Path
from typing import Any

from src.config import ROOT, load_config
from src.ingestion.scrape import read_sources

REQUIRED_FIELDS = {
    "doc_id",
    "scheme_name",
    "page_type",
    "source_url",
    "scraped_at",
    "sections",
}


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()


def load_records(scraped_dir: Path, allowed_sources: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_doc_ids: set[str] = set()
    for path in sorted(scraped_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        missing = REQUIRED_FIELDS.difference(record)
        if missing:
            raise ValueError(f"{path.name} is missing required fields: {sorted(missing)}")
        expected = allowed_sources.get(record["doc_id"])
        if expected is None or record["source_url"] != expected["url"]:
            raise ValueError(f"{path.name} is not one of the configured source documents")
        if record["scheme_name"] != expected["scheme_name"]:
            raise ValueError(f"{path.name} has an unexpected scheme name")
        if record["doc_id"] in seen_doc_ids:
            raise ValueError(f"Duplicate document ID in scraped files: {record['doc_id']}")
        seen_doc_ids.add(record["doc_id"])
        sections: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for section in record["sections"]:
            title = clean_text(section.get("title", ""))
            text = clean_text(section.get("text", ""))
            key = (title, text)
            if len(text) < 20 or key in seen:
                continue
            seen.add(key)
            sections.append({"title": title or "Overview", "text": text})
        if not sections:
            raise ValueError(f"{path.name} contains no usable text")
        records.append(
            {
                key: record[key]
                for key in (
                    "doc_id",
                    "scheme_name",
                    "page_type",
                    "source_url",
                    "scraped_at",
                )
            }
            | {"sections": sections}
        )
    expected_ids = set(allowed_sources)
    actual_ids = {record["doc_id"] for record in records}
    if actual_ids != expected_ids:
        raise ValueError(
            f"Expected exactly {len(expected_ids)} scraped documents; "
            f"found {len(actual_ids)}. Missing: {sorted(expected_ids - actual_ids)}"
        )
    return records


def run() -> int:
    cfg = load_config()
    sources = read_sources(ROOT / cfg["paths"]["sources"])
    allowed = {source["doc_id"]: source for source in sources}
    records = load_records(ROOT / cfg["paths"]["scraped"], allowed)
    output = ROOT / cfg["paths"]["loaded"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    for record in records:
        characters = sum(len(section["text"]) for section in record["sections"])
        print(
            f"{record['doc_id']:<48} "
            f"sections={len(record['sections']):<3} chars={characters}"
        )
    return len(records)


if __name__ == "__main__":
    run()
