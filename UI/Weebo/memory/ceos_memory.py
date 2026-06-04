from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


class CEOSMemory:
    """Read-only memory and proposal helper for the supervised Weebo layer."""

    CURRENT_TARGETS = {
        "UI/Weebo/patches/.keep",
        "UI/Weebo/patches/latest_patch_packet.yaml",
        "UI/Weebo/memory/active_mission.yaml",
        "UI/Weebo/memory/mission_memory.py",
        "UI/Weebo/memory/approved_proposals.yaml",
        "UI/Weebo/memory/rejected_proposals.yaml",
        "UI/Weebo/memory/decision_memory.py",
        "UI/Weebo/memory/SpaceshipDirectory.yaml",
        "UI/Weebo/memory/cards.yaml",
        "UI/Weebo/memory/ceos_memory.py",
        "UI/Weebo/contracts/proposal_contract.yaml",
        "UI/Weebo/weebo.py",
    }

    CE_OS_SOURCE_PREFIXES = (
        "Models/Shared/",
        "Models/Gear/",
        "Models/Godot/",
        "Models/Grant/",
        "Models/Cali/",
        "Models/Elrich/",
    )

    EXISTING_RUNTIME_PREFIXES = (
        "UI/scripts/",
        "UI/screen/",
    )

    BLOCKED_INGESTION_PREFIXES = (
        "local/",
        ".git/",
        ".godot/",
        "__pycache__/",
    )

    CE_OS_SOURCE_PATHS = {
        "UI/Mission.yaml",
        "UI/BOUNDARY.md",
    }

    def __init__(self, spaceship_root: Path | str | None = None):
        if spaceship_root is None:
            spaceship_root = Path(__file__).resolve().parents[3]

        self.root = Path(spaceship_root).resolve()
        self.weebo_root = self.root / "UI" / "Weebo"
        self.memory_root = self.weebo_root / "memory"
        self.contract_root = self.weebo_root / "contracts"
        self.patches_root = self.weebo_root / "patches"

        self.index_path = self.memory_root / "memory_sources.yaml"
        self.directory_path = self.memory_root / "SpaceshipDirectory.yaml"
        self.legacy_directory_path = self.memory_root / "Directory.yaml"
        self.cards_path = self.memory_root / "cards.yaml"
        self.proposal_contract_path = self.contract_root / "proposal_contract.yaml"
        self.latest_patch_packet_path = self.patches_root / "latest_patch_packet.yaml"

    def load_yaml_file(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}

        try:
            text = path.read_text(encoding="utf-8")
            loaded = yaml.safe_load(text) if yaml else self.simple_yaml_load(text)
            loaded = loaded or {}
        except Exception as exc:
            return {"_error": f"yaml_parse_error: {exc}", "_path": self.relative(path)}

        return loaded if isinstance(loaded, dict) else {"value": loaded}

    def simple_yaml_load(self, text: str) -> Any:
        """Parse the small YAML subset used by Weebo when PyYAML is unavailable."""
        rows = self._yaml_rows(text)
        if not rows:
            return {}

        value, _ = self._parse_yaml_block(rows, 0)
        return value

    def _yaml_rows(self, text: str) -> list[tuple[int, str]]:
        raw_lines = text.splitlines()
        rows: list[tuple[int, str]] = []
        index = 0

        while index < len(raw_lines):
            raw = raw_lines[index].rstrip()
            stripped = raw.strip()
            index += 1

            if not stripped or stripped.startswith("#"):
                continue

            indent = len(raw) - len(raw.lstrip(" "))
            if stripped.endswith(": >") or stripped.endswith(": |"):
                folded = stripped.endswith(": >")
                prefix = stripped[:-2].rstrip().rstrip(":")
                block_lines = []

                while index < len(raw_lines):
                    block_raw = raw_lines[index].rstrip()
                    block_stripped = block_raw.strip()
                    block_indent = len(block_raw) - len(block_raw.lstrip(" "))

                    if block_stripped and block_indent <= indent:
                        break

                    if block_stripped:
                        block_lines.append(block_stripped)
                    index += 1

                value = " ".join(block_lines) if folded else "\\n".join(block_lines)
                rows.append((indent, f"{prefix}: {value}"))
                continue

            rows.append((indent, stripped))

        return rows

    def _parse_yaml_block(self, rows: list[tuple[int, str]], index: int) -> tuple[Any, int]:
        if index >= len(rows):
            return {}, index

        block_indent = rows[index][0]
        is_list = rows[index][1].startswith("- ")

        if is_list:
            values = []
            while index < len(rows) and rows[index][0] == block_indent and rows[index][1].startswith("- "):
                content = rows[index][1][2:].strip()
                index += 1

                if not content:
                    if index < len(rows) and rows[index][0] > block_indent:
                        child, index = self._parse_yaml_block(rows, index)
                    else:
                        child = None
                    values.append(child)
                    continue

                if self._yaml_mapping_fragment(content):
                    key, raw_value = self._split_yaml_key_value(content)
                    item: dict[str, Any] = {}

                    if raw_value:
                        item[key] = self._parse_yaml_scalar(raw_value)
                    elif index < len(rows) and rows[index][0] > block_indent:
                        child, index = self._parse_yaml_block(rows, index)
                        item[key] = child
                    else:
                        item[key] = {}

                    while index < len(rows) and rows[index][0] > block_indent:
                        child, index = self._parse_yaml_block(rows, index)
                        if isinstance(child, dict):
                            item.update(child)
                        else:
                            item.setdefault("_items", child)

                    values.append(item)
                    continue

                values.append(self._parse_yaml_scalar(content))

            return values, index

        values = {}
        while index < len(rows) and rows[index][0] == block_indent and not rows[index][1].startswith("- "):
            key, raw_value = self._split_yaml_key_value(rows[index][1])
            index += 1

            if raw_value:
                values[key] = self._parse_yaml_scalar(raw_value)
            elif index < len(rows) and rows[index][0] > block_indent:
                child, index = self._parse_yaml_block(rows, index)
                values[key] = child
            else:
                values[key] = {}

        return values, index

    def _yaml_mapping_fragment(self, value: str) -> bool:
        if ":" not in value:
            return False
        key, _ = value.split(":", 1)
        return bool(key.strip()) and " " not in key.strip()

    def _split_yaml_key_value(self, value: str) -> tuple[str, str]:
        if ":" not in value:
            return value, ""
        key, raw_value = value.split(":", 1)
        return key.strip(), raw_value.strip()

    def _parse_yaml_scalar(self, value: str) -> Any:
        value = value.strip()
        lowered = value.lower()

        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none", "~"}:
            return None

        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        try:
            return int(value)
        except ValueError:
            return value

    def load_index(self) -> dict[str, Any]:
        return self.load_yaml_file(self.index_path)

    def load_directory(self) -> dict[str, Any]:
        if self.directory_path.exists():
            return self.load_yaml_file(self.directory_path)
        return self.load_yaml_file(self.legacy_directory_path)

    def load_cards(self) -> dict[str, Any]:
        return self.load_yaml_file(self.cards_path)

    def memory_cards(self) -> list[dict[str, Any]]:
        data = self.load_cards()

        if isinstance(data.get("value"), list):
            raw_cards = data["value"]
        elif isinstance(data.get("cards"), list):
            raw_cards = data["cards"]
        elif isinstance(data.get("WeeboCards", {}).get("cards"), list):
            raw_cards = data["WeeboCards"]["cards"]
        else:
            raw_cards = []

        cards = []
        for card in raw_cards:
            if not isinstance(card, dict):
                continue

            normalized = dict(card)
            normalized.setdefault("owns", [])
            normalized.setdefault("does_not_own", [])
            normalized.setdefault("keywords", [])
            normalized.setdefault("summary", "")
            normalized["source"] = self.normalize_path(normalized.get("source", ""))
            cards.append(normalized)

        return cards

    def card_aliases(self) -> dict[str, str]:
        return {
            "ceos": "ce_os",
            "ce-os": "ce_os",
            "ce_osv1": "ce_os",
            "ce-osv1": "ce_os",
            "contract": "contract",
            "authority": "contract",
            "boundary": "contract",
            "boundaries": "contract",
            "directory": "directory",
            "spaceshipdirectory": "directory",
            "spaceship_directory": "directory",
            "approved": "approved",
            "approval": "approved",
            "accepted": "approved",
            "rejected": "rejected",
            "reject": "rejected",
            "deadpaths": "rejected",
            "dead_paths": "rejected",
        }

    def get_card(self, query: str) -> dict[str, Any] | None:
        token = query.strip().lower().replace("-", "_").replace(" ", "_")
        wanted = self.card_aliases().get(token, token)

        for card in self.memory_cards():
            if card.get("id", "").lower() == wanted:
                return card

        return None

    def search_cards(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        terms = self.card_terms(query)
        matches = []

        for card in self.memory_cards():
            haystack = self._card_haystack(card)
            score = sum(1 for term in terms if term in haystack)
            exact_id = query.strip().lower().replace("-", "_") == card.get("id", "").lower()

            if not terms or score or exact_id:
                item = dict(card)
                item["score"] = score + (10 if exact_id else 0)
                matches.append(item)

        matches.sort(key=lambda item: (item["score"], item.get("id", "")), reverse=True)
        return matches[:limit] if limit else matches

    def card_terms(self, query: str) -> list[str]:
        stopwords = {
            "add",
            "build",
            "create",
            "source",
            "grounded",
            "memory",
            "card",
            "cards",
            "for",
            "this",
            "what",
            "file",
            "files",
            "purpose",
            "proposal",
            "proposals",
            "weebo",
        }
        cleaned = query.replace("_", " ").replace("-", " ").replace("/", " ")
        return [term.lower() for term in cleaned.split() if len(term) > 2 and term.lower() not in stopwords]

    def _card_haystack(self, card: dict[str, Any]) -> str:
        parts = [
            card.get("id", ""),
            card.get("source", ""),
            card.get("role", ""),
            card.get("summary", ""),
            " ".join(card.get("owns", []) or []),
            " ".join(card.get("does_not_own", []) or []),
            " ".join(card.get("keywords", []) or []),
        ]
        return " ".join(str(part) for part in parts).lower().replace("_", " ").replace("-", " ")

    def format_cards(self) -> str:
        cards = self.memory_cards()
        lines = ["AVAILABLE MEMORY CARDS", ""]

        if not cards:
            lines.append("- No memory cards loaded.")
            return "\n".join(lines)

        for card in cards:
            lines.append(f"- {card.get('id', '')}: {card.get('source', '')}")
            lines.append(f"  role: {card.get('role', '')}")

        return "\n".join(lines)

    def format_card(self, query: str) -> str:
        card = self.get_card(query)
        if not card:
            return "\n".join(
                [
                    "MEMORY CARD",
                    f"query: {query}",
                    "",
                    "- No matching memory card found.",
                ]
            )

        lines = [
            "MEMORY CARD",
            "",
            f"id: {card.get('id', '')}",
            f"source: {card.get('source', '')}",
            f"role: {card.get('role', '')}",
            "",
            "Owns:",
        ]
        lines.extend(f"- {item}" for item in card.get("owns", []) or [])
        lines.append("")
        lines.append("Does not own:")
        lines.extend(f"- {item}" for item in card.get("does_not_own", []) or [])
        lines.append("")
        lines.append("Keywords:")
        lines.extend(f"- {item}" for item in card.get("keywords", []) or [])
        lines.append("")
        lines.append("Summary:")
        lines.append(card.get("summary", ""))
        return "\n".join(lines)

    def format_memory_card_check(self, query: str) -> str:
        matches = self.search_cards(query, limit=3)
        lines = [
            "MEMORY CARD CHECK",
            f"query: {query}",
            "",
        ]

        if not matches:
            lines.append("- No specific memory card matched the query.")
            lines.append("- Available card ids: " + ", ".join(card.get("id", "") for card in self.memory_cards()))
            return "\n".join(lines)

        lines.append("Matching memory card(s):")
        for card in matches:
            lines.append(f"- {card.get('id', '')}: {card.get('source', '')}")
            lines.append(f"  role: {card.get('role', '')}")
            lines.append(f"  summary: {card.get('summary', '')}")

        return "\n".join(lines)

    def inspect(self, query: str, limit: int = 5, snippet_chars: int = 1200) -> dict[str, Any]:
        card = self.get_card(query)
        source_matches = self.search_source_files(query, limit=limit, snippet_chars=snippet_chars)

        if card and card.get("source"):
            card_source = self.source_file_record(card["source"], "memory_card_source", card.get("role", ""), snippet_chars)
            if card_source:
                source_matches = self._prepend_source_match(source_matches, card_source)

        return {
            "query": query,
            "card": card,
            "source_matches": source_matches,
        }

    def format_inspect(self, query: str) -> str:
        result = self.inspect(query)
        card = result["card"]
        source_matches = result["source_matches"]

        if not card and not source_matches:
            return "\n".join(
                [
                    "INSPECTION",
                    f"query: {query}",
                    "",
                    "- No indexed memory/source match found.",
                    "",
                    "Available commands:",
                    "- cards",
                    "- card <id>",
                    "- inspect <query>",
                    "- files <query>",
                    "- decided <query>",
                    "- mission",
                    "- propose <goal>",
                    "- patch-plan <task>",
                    "",
                    "Available cards:",
                    "- " + ", ".join(card.get("id", "") for card in self.memory_cards()),
                ]
            )

        lines = [
            "INSPECTION",
            f"query: {query}",
            "",
        ]

        if card:
            lines.extend(self._format_inspect_card(card))
            lines.append("")

        if source_matches:
            lines.append("MATCHING INDEXED SOURCE FILES")
            lines.append("")
            for match in source_matches:
                status = "exists" if match["exists"] else "missing"
                lines.append(f"- {match['path']} ({status})")
                lines.append(f"  category: {match['category']}")
                lines.append(f"  mutation_authority: {match['boundary']}")
                if match.get("role"):
                    lines.append(f"  role: {match['role']}")
                if match.get("snippet"):
                    lines.append("  snippet:")
                    lines.append("  ```text")
                    for snippet_line in match["snippet"].splitlines():
                        lines.append(f"  {snippet_line}")
                    lines.append("  ```")
                lines.append("")
        else:
            lines.append("MATCHING INDEXED SOURCE FILES")
            lines.append("")
            lines.append("- No indexed source file matched this query.")

        return "\n".join(lines).rstrip()

    def format_inspection_summary(self, query: str) -> str:
        result = self.inspect(query, limit=3, snippet_chars=500)
        card = result["card"]
        source_matches = result["source_matches"]
        lines = [
            "INSPECTION SUMMARY",
            f"query: {query}",
            "",
        ]

        if not card and not source_matches:
            lines.append("- No indexed memory/source match found.")
            lines.append("- Available cards: " + ", ".join(item.get("id", "") for item in self.memory_cards()))
            return "\n".join(lines)

        if card:
            lines.append(f"- card: {card.get('id', '')}")
            lines.append(f"  source: {card.get('source', '')}")
            lines.append(f"  role: {card.get('role', '')}")
            lines.append("  authority_warning: memory card is summary only; source remains authoritative.")

        if source_matches:
            lines.append("")
            lines.append("Top source matches:")
            for match in source_matches:
                status = "exists" if match["exists"] else "missing"
                lines.append(f"- {match['path']} ({status}, {match['category']}, {match['boundary']})")
                if match.get("snippet"):
                    snippet = " ".join(match["snippet"].split())
                    if len(snippet) > 220:
                        snippet = snippet[:217].rstrip() + "..."
                    lines.append(f"  snippet: {snippet}")

        return "\n".join(lines)

    def _format_inspect_card(self, card: dict[str, Any]) -> list[str]:
        lines = [
            "MEMORY CARD MATCH",
            "",
            f"card_id: {card.get('id', '')}",
            f"source_path: {card.get('source', '')}",
            f"role: {card.get('role', '')}",
            "",
            "owns:",
        ]
        lines.extend(f"- {item}" for item in card.get("owns", []) or [])
        lines.append("")
        lines.append("does_not_own:")
        lines.extend(f"- {item}" for item in card.get("does_not_own", []) or [])
        lines.append("")
        lines.append("keywords:")
        lines.extend(f"- {item}" for item in card.get("keywords", []) or [])
        lines.append("")
        lines.append("summary:")
        lines.append(card.get("summary", ""))
        lines.append("")
        lines.append("authority_warning: memory card is summary only; source file remains authoritative.")
        return lines

    def search_source_files(self, query: str, limit: int = 5, snippet_chars: int = 1200) -> list[dict[str, Any]]:
        terms = self.inspect_terms(query)
        if not terms:
            return []

        matches = []
        for record in self.known_path_records():
            if not record.get("exists"):
                continue

            abs_path = self.absolute_path(record["path"])
            text = self._read_source_text(abs_path)
            haystack = (
                f"{record['category']} {record['path']} {record.get('role', '')} {record.get('boundary', '')} {text}"
                .lower()
                .replace("_", " ")
                .replace("-", " ")
            )
            term_hits = [haystack.count(term) for term in terms]
            if len(terms) > 1 and any(hit == 0 for hit in term_hits):
                continue
            score = sum(term_hits)
            if not score:
                continue

            item = dict(record)
            item["score"] = score
            item["snippet"] = self.source_snippet(text, terms, snippet_chars)
            matches.append(item)

        matches.sort(key=lambda item: (item["score"], item["path"]), reverse=True)
        return matches[:limit]

    def source_file_record(
        self,
        rel_path: str,
        category: str,
        role: str,
        snippet_chars: int = 1200,
    ) -> dict[str, Any] | None:
        rel = self.normalize_path(rel_path)
        abs_path = self.absolute_path(rel)
        if not abs_path.exists():
            return {
                "category": category,
                "path": rel,
                "role": role,
                "exists": False,
                "boundary": self.classify_path(rel),
                "snippet": "",
                "score": 0,
            }

        text = self._read_source_text(abs_path)
        return {
            "category": category,
            "path": rel,
            "role": role,
            "exists": True,
            "boundary": self.classify_path(rel),
            "snippet": self.source_snippet(text, self.inspect_terms(rel), snippet_chars),
            "score": 100,
        }

    def source_snippet(self, text: str, terms: list[str], max_chars: int = 1200) -> str:
        if not text:
            return ""

        lowered = text.lower().replace("_", " ").replace("-", " ")
        first_hit = None
        for term in terms:
            hit = lowered.find(term)
            if hit != -1:
                first_hit = hit if first_hit is None else min(first_hit, hit)

        if first_hit is None:
            start = 0
        else:
            start = max(0, first_hit - 180)

        snippet = text[start : start + max_chars].strip()
        if start > 0:
            snippet = "... " + snippet
        if start + max_chars < len(text):
            snippet = snippet.rstrip() + " ..."
        if len(snippet) > max_chars:
            snippet = snippet[: max_chars - 3].rstrip() + "..."

        return snippet

    def inspect_terms(self, query: str) -> list[str]:
        stopwords = {
            "add",
            "build",
            "create",
            "inspect",
            "inspection",
            "source",
            "grounded",
            "memory",
            "card",
            "cards",
            "for",
            "this",
            "such",
            "none",
            "no",
            "what",
            "file",
            "files",
            "purpose",
            "proposal",
            "proposals",
            "weebo",
        }
        cleaned = query.replace("_", " ").replace("-", " ").replace("/", " ")
        return [term.lower() for term in cleaned.split() if len(term) > 2 and term.lower() not in stopwords]

    def _read_source_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _prepend_source_match(
        self,
        matches: list[dict[str, Any]],
        source_match: dict[str, Any],
    ) -> list[dict[str, Any]]:
        filtered = [match for match in matches if match.get("path") != source_match.get("path")]
        return [source_match] + filtered

    def load_proposal_contract(self) -> dict[str, Any]:
        return self.load_yaml_file(self.proposal_contract_path)

    def relative(self, path: Path | str) -> str:
        path = Path(path)
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix().replace("\\", "/")

    def normalize_path(self, path: Path | str) -> str:
        raw = str(path).replace("\\", "/").strip()
        if not raw:
            return raw

        candidate = Path(raw)
        if candidate.is_absolute():
            return self.relative(candidate)

        while raw.startswith("./"):
            raw = raw[2:]

        if raw.startswith("Spaceship/"):
            raw = raw[len("Spaceship/") :]

        return raw

    def absolute_path(self, rel_path: Path | str) -> Path:
        rel = self.normalize_path(rel_path)
        return self.root / rel

    def iter_sources(self):
        index = self.load_index()

        for category, paths in index.items():
            if category == "blocked_from_memory_ingestion":
                continue
            if not isinstance(paths, list):
                continue

            for rel_path in paths:
                rel = self.normalize_path(rel_path)
                yield category, rel, self.absolute_path(rel)

    def load_sources(self, max_chars_per_file: int = 6000) -> dict[str, list[dict[str, Any]] | list[str]]:
        loaded = []
        missing = []

        for category, rel_path, abs_path in self.iter_sources():
            if not abs_path.exists():
                missing.append(rel_path)
                continue

            text = abs_path.read_text(encoding="utf-8", errors="replace")
            loaded.append(
                {
                    "category": category,
                    "path": rel_path,
                    "chars": len(text),
                    "text": text[:max_chars_per_file],
                }
            )

        return {
            "loaded": loaded,
            "missing": missing,
        }

    def build_context(self, query: str = "", max_files: int = 12) -> str:
        data = self.load_sources()
        chunks = [
            "CE-OS PROJECT MEMORY",
            "These are repository memory sources. They are read-only context, not mutation authority.",
            "",
        ]

        missing = data["missing"]
        if missing:
            chunks.append("Missing memory sources:")
            for path in missing:
                chunks.append(f"- {path}")
            chunks.append("")

        loaded = data["loaded"]
        selected = self.find_paths(query, limit=max_files) if query else loaded[:max_files]
        selected_paths = {item["path"] for item in selected if "path" in item}

        for item in loaded:
            if query and item["path"] not in selected_paths:
                continue
            chunks.append(f"FILE: {item['path']}")
            chunks.append(f"CATEGORY: {item['category']}")
            chunks.append("```text")
            chunks.append(item["text"])
            chunks.append("```")
            chunks.append("")
            if len(selected_paths) and len([line for line in chunks if line.startswith("FILE: ")]) >= max_files:
                break

        return "\n".join(chunks)

    def inventory(self) -> str:
        data = self.load_sources(max_chars_per_file=1)
        categories: dict[str, list[str]] = {}

        for item in data["loaded"]:
            categories.setdefault(item["category"], []).append(item["path"])

        lines = ["CE-OS MEMORY INVENTORY", ""]

        for category, paths in categories.items():
            lines.append(f"{category}:")
            for path in paths:
                lines.append(f"  - {path}")
            lines.append("")

        if data["missing"]:
            lines.append("missing:")
            for path in data["missing"]:
                lines.append(f"  - {path}")

        return "\n".join(lines).rstrip()

    def terms(self, query: str) -> list[str]:
        cleaned = query.replace("_", " ").replace("-", " ").replace("/", " ")
        return [term.lower() for term in cleaned.split() if len(term) > 2]

    def known_path_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        seen: set[str] = set()

        for category, rel_path, abs_path in self.iter_sources():
            self._add_record(records, seen, category, rel_path, category, abs_path.exists())

        directory = self.load_directory().get("SpaceshipDirectory", {})
        primary_sources = directory.get("primary_memory_sources", {})
        for name, item in primary_sources.items():
            if isinstance(item, dict) and item.get("path"):
                self._add_record(records, seen, "primary_memory_sources", item["path"], item.get("role", name))

        active_systems = directory.get("active_systems", {})
        for name, item in active_systems.items():
            if not isinstance(item, dict):
                continue
            if item.get("path"):
                self._add_record(records, seen, "active_systems", item["path"], item.get("role", name))
            for rel_path in item.get("important_files", []) or []:
                self._add_record(records, seen, name, rel_path, item.get("role", name))

        cards = self.load_cards().get("WeeboCards", {}).get("cards", {})
        files_matter = cards.get("files_matter", {}).get("priority_groups", {})
        for group, items in files_matter.items():
            for item in items or []:
                if isinstance(item, dict) and item.get("path"):
                    self._add_record(records, seen, group, item["path"], item.get("reason", group))

        for card in self.memory_cards():
            if card.get("source"):
                self._add_record(records, seen, "memory_cards", card["source"], card.get("role", card.get("id", "")))

        for rel_path in self.CURRENT_TARGETS:
            self._add_record(records, seen, "current_Weebo_targets", rel_path, "current supervised build target")

        return records

    def _add_record(
        self,
        records: list[dict[str, Any]],
        seen: set[str],
        category: str,
        rel_path: str,
        role: str,
        exists: bool | None = None,
    ) -> None:
        rel = self.normalize_path(rel_path)
        if rel in seen:
            return
        seen.add(rel)
        if exists is None:
            exists = self.absolute_path(rel).exists()
        records.append(
            {
                "category": category,
                "path": rel,
                "role": role,
                "exists": exists,
                "boundary": self.classify_path(rel),
            }
        )

    def find_paths(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        terms = self.terms(query)
        matches = []

        for record in self.known_path_records():
            haystack = (
                f"{record['category']} {record['path']} {record.get('role', '')} {record.get('boundary', '')}"
                .lower()
                .replace("_", " ")
                .replace("-", " ")
            )
            score = sum(1 for term in terms if term in haystack)

            if score or not terms:
                item = dict(record)
                item["score"] = score
                matches.append(item)

        matches.sort(key=lambda item: (item["score"], item["path"]), reverse=True)
        return matches[:limit] if limit else matches

    def already_built_report(self, query: str, limit: int = 10) -> str:
        matches = self.find_paths(query, limit=limit)

        lines = [
            "ALREADY-BUILT CHECK",
            f"query: {query}",
            "",
        ]

        if not matches:
            lines.append("No indexed memory paths matched this query.")
            return "\n".join(lines)

        lines.append("Possible existing work:")
        for item in matches:
            status = "exists" if item["exists"] else "missing"
            lines.append(f"- [{item['category']}] {item['path']} ({status}, {item['boundary']})")

        return "\n".join(lines)

    def existing_work(self, query: str = "") -> dict[str, Any]:
        directory = self.load_directory().get("SpaceshipDirectory", {})
        systems = []

        for name, item in (directory.get("active_systems", {}) or {}).items():
            if not isinstance(item, dict):
                continue
            systems.append(
                {
                    "name": name,
                    "path": item.get("path", ""),
                    "role": item.get("role", ""),
                    "status": item.get("status", ""),
                    "exists": self.absolute_path(item.get("path", "")).exists() if item.get("path") else False,
                    "mutation": item.get("weebo_mutation", self.classify_path(item.get("path", ""))),
                }
            )

        return {
            "question": "What already exists?",
            "systems": systems,
            "matching_paths": self.find_paths(query, limit=10) if query else [],
        }

    def format_existing_work(self, query: str = "") -> str:
        data = self.existing_work(query)
        lines = ["WHAT ALREADY EXISTS", ""]

        if data["systems"]:
            for system in data["systems"]:
                status = "exists" if system["exists"] else "missing"
                lines.append(f"- {system['name']}: {system['path']} ({status})")
                lines.append(f"  role: {system['role']}")
                lines.append(f"  mutation: {system['mutation']}")
        else:
            lines.append("- No active system map loaded.")

        if data["matching_paths"]:
            lines.append("")
            lines.append("Query matches:")
            for item in data["matching_paths"]:
                status = "exists" if item["exists"] else "missing"
                lines.append(f"- {item['path']} ({status}, {item['boundary']})")

        return "\n".join(lines)

    def important_files(self, query: str = "") -> list[dict[str, Any]]:
        if query:
            return self.find_paths(query, limit=12)

        cards = self.load_cards().get("WeeboCards", {}).get("cards", {})
        priority_groups = cards.get("files_matter", {}).get("priority_groups", {})
        records = []

        for group, items in priority_groups.items():
            for item in items or []:
                if not isinstance(item, dict) or not item.get("path"):
                    continue
                rel = self.normalize_path(item["path"])
                records.append(
                    {
                        "category": group,
                        "path": rel,
                        "role": item.get("reason", ""),
                        "exists": self.absolute_path(rel).exists(),
                        "boundary": item.get("mutation", self.classify_path(rel)),
                    }
                )

        if not records:
            for card in self.memory_cards():
                rel = card.get("source", "")
                if not rel:
                    continue
                records.append(
                    {
                        "category": "memory_cards",
                        "path": rel,
                        "role": card.get("role", ""),
                        "exists": self.absolute_path(rel).exists(),
                        "boundary": self.classify_path(rel),
                    }
                )

        return records

    def format_important_files(self, query: str = "") -> str:
        lines = ["WHICH FILES MATTER", ""]
        files = self.important_files(query)

        if not files:
            lines.append("- No file cards loaded.")
            return "\n".join(lines)

        for item in files:
            status = "exists" if item["exists"] else "missing"
            lines.append(f"- [{item['category']}] {item['path']} ({status})")
            lines.append(f"  role: {item['role']}")
            lines.append(f"  boundary: {item['boundary']}")

        return "\n".join(lines)

    def authority_boundaries(self) -> list[str]:
        cards = self.load_cards().get("WeeboCards", {}).get("cards", {})
        boundary_card = cards.get("authority_boundaries", {})
        boundaries = []

        for item in boundary_card.get("boundaries", []) or []:
            owner = item.get("owner", "unknown")
            rule = item.get("Weebo_rule", "")
            owns = ", ".join(item.get("owns", []) or [])
            boundaries.append(f"{owner}: {rule}; owns {owns}")

        if not boundaries:
            boundaries = [
                "Seth: final human approval authority",
                "Weebo: observe, summarize, rank files, and propose only",
                "CE-OS source files: read-only unless Seth explicitly approves mutation",
                "Runtime and display surfaces: not evidence or validation",
            ]

        return boundaries

    def format_authority_boundaries(self) -> str:
        lines = ["AUTHORITY BOUNDARIES", ""]
        for boundary in self.authority_boundaries():
            lines.append(f"- {boundary}")
        lines.append("")
        lines.append("Blocked promotions:")
        for item in self.blocked_promotions():
            lines.append(f"- {item}")
        return "\n".join(lines)

    def blocked_promotions(self) -> list[str]:
        cards = self.load_cards().get("WeeboCards", {}).get("cards", {})
        boundary_card = cards.get("authority_boundaries", {})
        return boundary_card.get("prohibited_promotions", []) or [
            "proposal_equals_patch",
            "display_equals_evidence",
            "runtime_health_equals_readiness",
        ]

    def classify_path(self, path: Path | str) -> str:
        rel = self.normalize_path(path)
        rel_lower = rel.lower()

        for blocked in self.BLOCKED_INGESTION_PREFIXES:
            if rel_lower.startswith(blocked.lower()):
                return "blocked_from_memory_ingestion"

        current_targets_lower = {item.lower() for item in self.CURRENT_TARGETS}
        if rel_lower in current_targets_lower:
            return "current_Weebo_target"

        if rel in self.CE_OS_SOURCE_PATHS:
            return "blocked_read_only_CE_OS_source"

        if any(rel.startswith(prefix) for prefix in self.CE_OS_SOURCE_PREFIXES):
            return "blocked_read_only_CE_OS_source"

        if any(rel.startswith(prefix) for prefix in self.EXISTING_RUNTIME_PREFIXES):
            return "requires_Seth_approval_existing_runtime"

        if rel.startswith("UI/Weebo/"):
            return "Weebo_internal_review_before_change"

        return "requires_Seth_approval_unknown_or_external_to_Weebo_scope"

    def approval_items(self, goal: str = "", candidate_files: list[str] | None = None) -> list[str]:
        items = [
            "Seth approval is required before accepting or rejecting the proposal.",
        ]
        goal_lower = goal.lower()

        if "jarvis" in goal_lower:
            items.append("Jarvis construction or wiring waits for Seth approval.")

        if "autonomous" in goal_lower or "auto edit" in goal_lower or "apply patch" in goal_lower:
            items.append("Autonomous edit wiring or patch application waits for Seth approval.")

        for rel in candidate_files or []:
            boundary = self.classify_path(rel)
            if boundary == "blocked_read_only_CE_OS_source":
                items.append(f"{self.normalize_path(rel)} is a CE-OS source path and must remain read-only here.")
            elif boundary == "requires_Seth_approval_existing_runtime":
                items.append(f"{self.normalize_path(rel)} is existing runtime/dashboard code and waits for Seth approval.")
            elif boundary not in {"current_Weebo_target", "Weebo_internal_review_before_change"}:
                items.append(f"{self.normalize_path(rel)} is outside the current Weebo target scope and waits for Seth approval.")

        return self._dedupe(items)

    def format_approval_items(self, goal: str = "", candidate_files: list[str] | None = None) -> str:
        lines = ["WHAT WAITS FOR SETH APPROVAL", ""]
        for item in self.approval_items(goal, candidate_files):
            lines.append(f"- {item}")
        return "\n".join(lines)

    def make_proposal(self, goal: str, candidate_files: list[str] | None = None) -> dict[str, Any]:
        candidate_files = candidate_files or self._infer_files_from_goal(goal)
        relevant_files = self._proposal_files(goal, candidate_files)
        waits_for_seth = self.approval_items(goal, [item["path"] for item in relevant_files])
        goal_lower = goal.lower()
        blocked_by_goal = []

        if "jarvis" in goal_lower:
            blocked_by_goal.append("Jarvis work is explicitly deferred.")
        if "autonomous" in goal_lower or "apply patch" in goal_lower:
            blocked_by_goal.append("Autonomous edit or patch application is outside Weebo authority.")

        return {
            "proposal_id": "weebo-supervised-proposal-v0",
            "status": "proposal_only_pending_seth_review" if waits_for_seth else "proposal_only",
            "goal": goal,
            "what_already_exists": self.existing_work(goal),
            "relevant_files": relevant_files,
            "authority_boundaries": self.authority_boundaries(),
            "safe_proposal": {
                "safe_to_make_now": True,
                "action": "Draft and present a bounded proposal for Seth review.",
                "scope": "memory_summary_file_relevance_authority_boundary_and_review_gate_only",
                "blocked_by_goal": blocked_by_goal,
            },
            "waits_for_seth": waits_for_seth,
            "non_actions": self.default_non_actions(),
        }

    def _proposal_files(self, goal: str, candidate_files: list[str]) -> list[dict[str, Any]]:
        records = []
        seen = set()

        for rel in candidate_files:
            normalized = self.normalize_path(rel)
            if normalized in seen:
                continue
            seen.add(normalized)
            records.append(
                {
                    "path": normalized,
                    "exists": self.absolute_path(normalized).exists(),
                    "boundary": self.classify_path(normalized),
                }
            )

        for item in self.find_paths(goal, limit=8):
            normalized = item["path"]
            if normalized in seen:
                continue
            seen.add(normalized)
            records.append(
                {
                    "path": normalized,
                    "exists": item["exists"],
                    "boundary": item["boundary"],
                    "role": item.get("role", ""),
                }
            )

        return records

    def _infer_files_from_goal(self, goal: str) -> list[str]:
        inferred = []
        goal_lower = goal.lower()
        for target in self.CURRENT_TARGETS:
            name = Path(target).name.lower()
            stem = Path(target).stem.lower()
            if name in goal_lower or stem in goal_lower:
                inferred.append(target)

        if not inferred and "weebo" in goal_lower:
            inferred.extend(sorted(self.CURRENT_TARGETS))

        return inferred

    def default_non_actions(self) -> list[str]:
        contract = self.load_proposal_contract().get("ProposalContract", {})
        return contract.get("default_non_actions", []) or [
            "no_CE_OS_source_file_mutation",
            "no_autonomous_edits",
            "no_Jarvis_build",
            "no_runtime_validation_claim",
            "no_canon_promotion",
        ]

    def format_proposal(self, goal: str, candidate_files: list[str] | None = None) -> str:
        proposal = self.make_proposal(goal, candidate_files)
        lines = [
            "SAFE PROPOSAL",
            "",
            f"id: {proposal['proposal_id']}",
            f"status: {proposal['status']}",
            f"goal: {proposal['goal']}",
            "",
            "Relevant files:",
        ]

        for item in proposal["relevant_files"]:
            status = "exists" if item["exists"] else "missing"
            role = f", {item['role']}" if item.get("role") else ""
            lines.append(f"- {item['path']} ({status}, {item['boundary']}{role})")

        lines.extend(["", "Authority boundaries:"])
        for item in proposal["authority_boundaries"]:
            lines.append(f"- {item}")

        lines.extend(["", "Safe next step:"])
        lines.append(f"- {proposal['safe_proposal']['action']}")
        if proposal["safe_proposal"]["blocked_by_goal"]:
            for item in proposal["safe_proposal"]["blocked_by_goal"]:
                lines.append(f"- blocked: {item}")

        lines.extend(["", "Waits for Seth:"])
        for item in proposal["waits_for_seth"]:
            lines.append(f"- {item}")

        lines.extend(["", "Non-actions:"])
        for item in proposal["non_actions"]:
            lines.append(f"- {item}")

        return "\n".join(lines)

    def write_patch_packet(self, task: str) -> dict[str, Any]:
        packet = self.build_patch_packet(task)
        self.patches_root.mkdir(parents=True, exist_ok=True)
        self.latest_patch_packet_path.write_text(self.packet_to_yaml(packet), encoding="utf-8")
        return {
            "path": self.relative(self.latest_patch_packet_path),
            "packet": packet,
        }

    def build_patch_packet(self, task: str) -> dict[str, Any]:
        task = task.strip() or "Unspecified supervised Weebo patch plan"
        proposal = self.make_proposal(task)
        target_files = self.patch_packet_target_files(task, proposal["relevant_files"])

        risks = [
            "Packet is review-only; treating it as approval would violate Weebo boundaries.",
            "Any listed CE-OS source path must remain read-only unless Seth explicitly approves a separate edit.",
            "Any existing runtime/dashboard file listed in target_files requires Seth approval before editing.",
        ]
        uncertainties = [
            "Exact implementation remains undecided until Seth reviews the packet.",
            "Target files are inferred from indexed memory matches and may need human pruning.",
            "No patch contents have been generated or applied.",
        ]

        return {
            "status": "PROPOSED_ONLY",
            "task": task,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "target_files": self._dedupe(target_files),
            "rationale": [
                "Run existing-file, authority-boundary, prior-decision, active-mission, memory-card, and inspection checks before planning edits.",
                "Create a reviewable packet for Seth without mutating target files or applying patches.",
            ],
            "risks": risks,
            "uncertainties": uncertainties,
            "proposed_changes": [
                "Review the preflight output for existing source matches and authority limits.",
                "If Seth approves, prepare a separate supervised implementation pass scoped to approved files.",
                "Keep this packet in PROPOSED_ONLY status until explicit approval is recorded elsewhere.",
            ],
            "approval_required": True,
            "blocked_actions": [
                "no_direct_edit",
                "no_apply",
                "no_commit",
                "no_CE_OS_source_mutation",
                "no_Jarvis_build",
            ],
        }

    def patch_packet_target_files(self, task: str, relevant_files: list[dict[str, Any]]) -> list[str]:
        task_lower = task.lower()
        targets: list[str] = []

        if "card" in task_lower:
            targets.append("UI/Weebo/memory/cards.yaml")

        if "inspect" in task_lower or "inspection" in task_lower or "command" in task_lower:
            targets.extend(
                [
                    "UI/Weebo/memory/ceos_memory.py",
                    "UI/Weebo/weebo.py",
                ]
            )

        if "decision" in task_lower or "decided" in task_lower:
            targets.extend(
                [
                    "UI/Weebo/memory/approved_proposals.yaml",
                    "UI/Weebo/memory/rejected_proposals.yaml",
                    "UI/Weebo/memory/decision_memory.py",
                ]
            )

        if "mission" in task_lower or "focus" in task_lower or "next" in task_lower:
            targets.extend(
                [
                    "UI/Weebo/memory/active_mission.yaml",
                    "UI/Weebo/memory/mission_memory.py",
                ]
            )

        if not targets:
            for item in relevant_files:
                path = item.get("path", "")
                if path.startswith("UI/Weebo/") and not path.endswith("/"):
                    targets.append(path)

        if not targets:
            targets.append("UI/Weebo/patches/latest_patch_packet.yaml")

        return self._dedupe(targets)

    def format_patch_packet_summary(self, write_result: dict[str, Any]) -> str:
        packet = write_result["packet"]
        lines = [
            "PATCH PACKET WRITTEN",
            "",
            f"path: {write_result['path']}",
            f"status: {packet['status']}",
            f"task: {packet['task']}",
            f"approval_required: {str(packet['approval_required']).lower()}",
            "",
            "Target files:",
        ]
        lines.extend(f"- {path}" for path in packet["target_files"])
        lines.append("")
        lines.append("Blocked actions:")
        lines.extend(f"- {action}" for action in packet["blocked_actions"])
        lines.append("")
        lines.append("Summary: review packet only; no target files edited, no patch applied, no approval marked.")
        return "\n".join(lines)

    def packet_to_yaml(self, packet: dict[str, Any]) -> str:
        lines: list[str] = []
        for key in [
            "status",
            "task",
            "created_at",
            "target_files",
            "rationale",
            "risks",
            "uncertainties",
            "proposed_changes",
            "approval_required",
            "blocked_actions",
        ]:
            value = packet[key]
            if isinstance(value, bool):
                lines.append(f"{key}: {'true' if value else 'false'}")
            elif isinstance(value, list):
                lines.append(f"{key}:")
                if not value:
                    lines.append("  []")
                for item in value:
                    lines.append(f"  - {self._yaml_scalar(item)}")
            else:
                lines.append(f"{key}: {self._yaml_scalar(value)}")
        lines.append("")
        return "\n".join(lines)

    def _yaml_scalar(self, value: Any) -> str:
        text = str(value)
        if not text:
            return '""'
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def supervised_brief(self, query: str = "Weebo supervised memory proposal layer") -> str:
        sections = [
            self.format_existing_work(query),
            self.format_important_files(query),
            self.format_authority_boundaries(),
            self.format_proposal(query),
            self.format_approval_items(query),
        ]
        return "\n\n".join(sections)

    def answer(self, question: str) -> str:
        question_lower = question.lower()

        if "already" in question_lower or "exist" in question_lower:
            return self.format_existing_work(question)
        if "file" in question_lower and "matter" in question_lower:
            return self.format_important_files(question)
        if "authority" in question_lower or "boundar" in question_lower:
            return self.format_authority_boundaries()
        if "proposal" in question_lower or "safe" in question_lower:
            return self.format_proposal(question)
        if "approval" in question_lower or "seth" in question_lower or "wait" in question_lower:
            return self.format_approval_items(question)

        return self.supervised_brief(question)

    def _dedupe(self, items: list[str]) -> list[str]:
        seen = set()
        result = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result
