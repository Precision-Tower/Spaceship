from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path
from Agency.Core.foundation.paths import DASHBOARD_ROOT

import chromadb
from sentence_transformers import SentenceTransformer

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INCLUDE_SUFFIXES = {".py", ".gd", ".yaml", ".yml", ".md", ".txt", ".tscn", ".json"}
IGNORE_PARTS = {".git", ".godot", "__pycache__", "Chroma", "local", "old"}
IGNORE_FILENAMES = {
    "current_context_brief.yaml",
}


def available_memory_agents() -> list[str]:
    agents_root = DASHBOARD_ROOT / "Agency" / "Agents"
    if not agents_root.exists():
        return []
    return sorted(
        path.name
        for path in agents_root.iterdir()
        if path.is_dir() and (path / "memory" / "sources.yaml").exists()
    )


def should_skip(path: Path) -> bool:
    if set(path.parts) & IGNORE_PARTS:
        return True

    if path.name in IGNORE_FILENAMES:
        return True

    return False


def chunk_text(text: str, max_chars: int = 1800, overlap: int = 200) -> list[str]:
    text = text.replace("\r\n", "\n")
    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)

    return chunks


def file_id(path: Path, chunk_index: int) -> str:
    rel = path.relative_to(DASHBOARD_ROOT).as_posix()
    raw = f"{rel}:{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def expand_sources(source_patterns: list[str]) -> list[Path]:
    files: list[Path] = []

    for pattern in source_patterns:
        matches = list(DASHBOARD_ROOT.glob(pattern))

        for match in matches:
            if match.is_file():
                files.append(match)
            elif match.is_dir():
                for path in match.rglob("*"):
                    if path.is_file():
                        files.append(path)

    output = []
    for path in sorted(set(files)):
        if should_skip(path):
            continue
        if path.suffix.lower() not in INCLUDE_SUFFIXES:
            continue
        output.append(path)

    return output


def load_sources(agent: str) -> dict:
    sources_path = DASHBOARD_ROOT / "Agency" / "Agents" / agent / "memory" / "sources.yaml"
    data = yaml.safe_load(sources_path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"invalid sources.yaml: {sources_path}")

    memory = data.get("MemorySources")

    if not isinstance(memory, dict):
        raise ValueError(f"missing MemorySources mapping: {sources_path}")

    sources = memory.get("sources", [])
    excludes = memory.get("exclude", [])

    if not isinstance(sources, list):
        raise ValueError(f"MemorySources.sources must be a list: {sources_path}")

    if not isinstance(excludes, list):
        raise ValueError(f"MemorySources.exclude must be a list: {sources_path}")

    return memory


def build_agent_index(agent: str) -> int:
    memory = load_sources(agent)
    sources = memory.get("sources", [])
    excludes = memory.get("exclude", [])

    chroma_dir = DASHBOARD_ROOT / "Agency" / "Agents" / agent / "memory" / "Chroma"
    collection_name = f"{agent.lower()}_memory"

    files = expand_sources(sources)

    if excludes:
        excluded_paths = set()

        for pattern in excludes:
            excluded_paths.update(
                path.resolve()
                for path in DASHBOARD_ROOT.glob(pattern)
                if path.is_file()
            )

        files = [
            path
            for path in files
            if path.resolve() not in excluded_paths
        ]

    print(f"AGENT: {agent}")
    print(f"CHROMA_DIR: {chroma_dir}")
    print(f"COLLECTION: {collection_name}")
    print(f"FILES_FOUND: {len(files)}")

    if not files:
        print("NO_FILES_FOUND")
        return 1

    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)

    chroma_dir.mkdir(parents=True, exist_ok=True)

    embedder = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "owner": agent,
            "authority": "retrieval_only_not_source_authority",
        },
    )

    ids = []
    documents = []
    metadatas = []

    for path in files:
        rel = path.relative_to(DASHBOARD_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")

        for i, chunk in enumerate(chunk_text(text)):
            ids.append(file_id(path, i))
            documents.append(chunk)
            metadatas.append(
                {
                    "owner": agent,
                    "path": rel,
                    "chunk_index": i,
                    "authority": "retrieval_only_not_source_authority",
                }
            )

    embeddings = embedder.encode(
        documents,
        batch_size=16,
        show_progress_bar=True,
        normalize_embeddings=True,
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print("INDEX_BUILT")
    print(f"CHUNKS_INDEXED: {len(documents)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent", choices=available_memory_agents() or None)
    args = parser.parse_args()
    return build_agent_index(args.agent)


if __name__ == "__main__":
    raise SystemExit(main())
