
import argparse
import json
from datetime import date
from pathlib import Path
from .source_providers import download_official_source
from .corpus_integrity import sha256_file


def refresh(base_dir: Path) -> None:
    manifest_path = base_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    for document in manifest["documents"]:
        source_path = base_dir / document["files"]["source_path"]
        downloaded = download_official_source(document)
        old_hash = document.get("hashes", {}).get("source_sha256")
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(downloaded.payload)
        document["source"]["retrieved_at"] = today
        document["source"]["resolved_url"] = downloaded.final_url
        document["source"]["content_type"] = downloaded.content_type
        hashes = document.setdefault("hashes", {})
        hashes["source_sha256"] = sha256_file(source_path)
        if old_hash != hashes["source_sha256"]:
            hashes.pop("normalized_sha256", None)
            document["normalization"] = {"status": "stale", "reason": "source_changed"}
    manifest["generated_at"] = today
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_dir", type=Path)
    args = parser.parse_args()
    refresh(args.base_dir)
