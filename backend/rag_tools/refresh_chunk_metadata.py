
import argparse
import json
from pathlib import Path


def refresh(chunks_input: Path, corpus_dir: Path) -> None:
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    documents = {document["law_key"]: document for document in manifest["documents"]}
    chunks = []
    counts = {}
    for line in chunks_input.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        chunk = json.loads(line)
        document = documents[chunk["law_key"]]
        chunk.update({
            "doc_version": manifest["version"],
            "jurisdiction": manifest["jurisdiction"],
            "language": manifest["language"],
            "source_url": document["source"]["url"],
            "retrieved_at": document["source"]["retrieved_at"],
        })
        chunks.append(chunk)
        counts[chunk["law_key"]] = counts.get(chunk["law_key"], 0) + 1
    chunks_dir = corpus_dir / "chunks"
    (chunks_dir / "chunks.jsonl").write_text(
        "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks), encoding="utf-8"
    )
    (chunks_dir / "chunks_stats.json").write_text(
        json.dumps({"total": len(chunks), "by_law": counts}, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("chunks_input", type=Path)
    parser.add_argument("corpus_dir", type=Path)
    args = parser.parse_args()
    refresh(args.chunks_input, args.corpus_dir)
