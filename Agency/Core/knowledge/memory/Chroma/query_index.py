from __future__ import annotations

import argparse
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


from Agency.Core.foundation.paths import DASHBOARD_ROOT
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EXACT_PATH_CANDIDATE_COUNT = 25


def available_memory_agents() -> list[str]:
    agents_root = DASHBOARD_ROOT / "Agency" / "Agents"
    if not agents_root.exists():
        return []
    return sorted(
        path.name
        for path in agents_root.iterdir()
        if path.is_dir() and (path / "memory" / "sources.yaml").exists()
    )
INDEXED_EXTENSIONS = (
    "py",
    "gd",
    "yaml",
    "yml",
    "md",
    "txt",
    "tscn",
    "json",
)
FILE_MENTION_RE = re.compile(
    r"(?i)(?:^|[^\w./\\-])"
    r"([A-Za-z0-9_./\\-]+\.("
    + "|".join(INDEXED_EXTENSIONS)
    + r"))"
    r"(?![\w./\\-])"
)


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").strip().strip("'\"`").lower().lstrip("./")


def _extract_file_mentions(query: str) -> list[str]:
    mentions: list[str] = []

    for match in FILE_MENTION_RE.finditer(query):
        mention = _normalize_path(match.group(1))

        if mention and mention not in mentions:
            mentions.append(mention)

        filename = mention.rsplit("/", 1)[-1]
        if filename and filename not in mentions:
            mentions.append(filename)

    return mentions


def _path_matches_file_mention(path: str, mentions: list[str]) -> bool:
    normalized_path = _normalize_path(path)

    for mention in mentions:
        if normalized_path == mention or normalized_path.endswith(f"/{mention}"):
            return True

    return False


def _boost_exact_path_matches(rows: list[dict], query: str) -> list[dict]:
    mentions = _extract_file_mentions(query)

    if not mentions:
        return rows

    ranked_rows = sorted(
        enumerate(rows),
        key=lambda item: (
            0
            if _path_matches_file_mention(
                str(item[1].get("path", "")),
                mentions,
            )
            else 1,
            item[0],
        ),
    )

    return [row for _, row in ranked_rows]


def _candidate_count_for_query(collection, query: str, n_results: int) -> int:
    if not _extract_file_mentions(query):
        return n_results

    candidate_count = max(n_results, EXACT_PATH_CANDIDATE_COUNT)

    try:
        collection_count = collection.count()
    except Exception:
        return candidate_count

    if collection_count <= 0:
        return n_results

    return min(candidate_count, collection_count)


def retrieve_agent_memory(
    agent: str,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    chroma_dir = DASHBOARD_ROOT / "Agency" / "Agents" / agent / "memory" / "Chroma"
    collection_name = f"{agent.lower()}_memory"

    if not chroma_dir.exists():
        return []

    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(name=collection_name)

    embedder = SentenceTransformer(MODEL_NAME)
    query_embedding = embedder.encode(
        [query],
        normalize_embeddings=True,
    ).tolist()[0]

    candidate_count = _candidate_count_for_query(collection, query, n_results)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    rows = []

    for index, doc in enumerate(docs):
        meta = metas[index] if index < len(metas) else {}

        rows.append({
            "id": ids[index] if index < len(ids) else "UNKNOWN",
            "path": meta.get("path", "UNKNOWN"),
            "chunk_index": meta.get("chunk_index", "UNKNOWN"),
            "distance": distances[index] if index < len(distances) else None,
            "authority": meta.get("authority", "retrieval_only_not_source_authority"),
            "document": doc,
        })

    rows = _boost_exact_path_matches(rows, query)

    return rows[:n_results]

def query_agent_index(agent: str, query: str, n_results: int = 5) -> int:
    chroma_dir = DASHBOARD_ROOT / "Agency" / "Agents" / agent / "memory" / "Chroma"
    collection_name = f"{agent.lower()}_memory"

    print("VECTOR_QUERY")
    print(f"agent: {agent}")
    print(f"query: {query}")
    print(f"collection: {collection_name}")
    print(f"chroma_dir: {chroma_dir}")
    print("authority: retrieval_only_not_source_authority")
    print()

    rows = retrieve_agent_memory(
        agent=agent,
        query=query,
        n_results=n_results,
    )

    if not rows:
        print("NO_RESULTS")
        return 1

    for index, row in enumerate(rows, start=1):
        preview = str(row["document"]).strip()

        if len(preview) > 1200:
            preview = preview[:1200].rstrip() + "\n...[truncated]"

        print(f"--- RESULT {index} ---")
        print(f"id: {row['id']}")
        print(f"path: {row['path']}")
        print(f"chunk_index: {row['chunk_index']}")
        print(f"distance: {row['distance']}")
        print(f"authority: {row['authority']}")
        print("snippet: |")

        for line in preview.splitlines():
            print(f"  {line}")

        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent", choices=available_memory_agents() or None)
    parser.add_argument("query", nargs="+")
    parser.add_argument("--n", type=int, default=5)

    args = parser.parse_args()
    query = " ".join(args.query).strip()

    if not query:
        print("ERR: empty query")
        return 2

    return query_agent_index(args.agent, query, n_results=args.n)


if __name__ == "__main__":
    raise SystemExit(main())
