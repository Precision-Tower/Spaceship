from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


class DecisionMemory:
    """Read-only approved/rejected proposal memory for Weebo."""

    def __init__(self, spaceship_root: Path | str | None = None):
        if spaceship_root is None:
            spaceship_root = Path(__file__).resolve().parents[3]

        self.root = Path(spaceship_root).resolve()
        self.memory_root = self.root / "UI" / "Weebo" / "memory"
        self.approved_path = self.memory_root / "approved_proposals.yaml"
        self.rejected_path = self.memory_root / "rejected_proposals.yaml"

    def list_approved(self) -> list[dict[str, Any]]:
        return self._load_decisions(self.approved_path, "approved_proposals", "APPROVED")

    def list_rejected(self) -> list[dict[str, Any]]:
        return self._load_decisions(self.rejected_path, "rejected_proposals", "REJECTED")

    def search_decisions(self, query: str) -> list[dict[str, Any]]:
        terms = self._terms(query)
        matches = []

        for decision in self.list_approved() + self.list_rejected():
            haystack = self._search_blob(decision)
            score = sum(1 for term in terms if term in haystack)
            exact_phrase = query.strip().lower() in haystack if query.strip() else False
            threshold = 1 if len(terms) <= 1 else min(2, len(terms))

            if not terms or exact_phrase or score >= threshold:
                item = dict(decision)
                item["score"] = score + (len(terms) + 2 if exact_phrase else 0)
                matches.append(item)

        matches.sort(key=lambda item: (item["score"], item.get("date", ""), item.get("id", "")), reverse=True)
        return matches

    def already_decided(self, query: str) -> dict[str, Any]:
        matches = self.search_decisions(query)
        return {
            "query": query,
            "decided": bool(matches),
            "matches": matches,
        }

    def format_decisions(self) -> str:
        return "\n\n".join([self.format_approved(), self.format_rejected()])

    def format_approved(self) -> str:
        return self._format_list("APPROVED DECISIONS", self.list_approved())

    def format_rejected(self) -> str:
        return self._format_list("REJECTED DECISIONS", self.list_rejected())

    def format_already_decided(self, query: str) -> str:
        result = self.already_decided(query)
        lines = [
            "PRIOR DECISION CHECK",
            f"query: {query}",
            "",
        ]

        if not result["decided"]:
            lines.append("- No matching prior decision found.")
            return "\n".join(lines)

        lines.append("Matching prior decision(s):")
        for decision in result["matches"]:
            lines.extend(self._format_decision_lines(decision))

        return "\n".join(lines)

    def _load_decisions(self, path: Path, key: str, required_status: str) -> list[dict[str, Any]]:
        if not path.exists():
            return []

        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) if yaml else self._fallback_load(text, key)
        records = data.get(key, []) if isinstance(data, dict) else []

        decisions = []
        for record in records or []:
            if not isinstance(record, dict):
                continue

            decision = dict(record)
            decision["status"] = required_status

            if required_status == "APPROVED":
                decision.setdefault("affected_files", [])
                decision.setdefault("rationale", "")
            else:
                decision.setdefault("rejection_reason", "")

            decisions.append(decision)

        return decisions

    def _fallback_load(self, text: str, key: str) -> dict[str, list[dict[str, Any]]]:
        records = []
        current: dict[str, Any] | None = None
        active_list_key: str | None = None

        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped == f"{key}:":
                continue

            if stripped.startswith("- id:"):
                if current:
                    records.append(current)
                current = {"id": self._clean_scalar(stripped.split(":", 1)[1])}
                active_list_key = None
                continue

            if current is None:
                continue

            if stripped.endswith(":") and not stripped.startswith("- "):
                active_list_key = stripped[:-1].strip()
                current[active_list_key] = []
                continue

            if active_list_key and stripped.startswith("- "):
                current[active_list_key].append(self._clean_scalar(stripped[2:]))
                continue

            if ":" in stripped:
                active_list_key = None
                field, value = stripped.split(":", 1)
                current[field.strip()] = self._clean_scalar(value)

        if current:
            records.append(current)

        return {key: records}

    def _format_list(self, title: str, decisions: list[dict[str, Any]]) -> str:
        lines = [title, ""]
        if not decisions:
            lines.append("- No decisions recorded.")
            return "\n".join(lines)

        for decision in decisions:
            lines.extend(self._format_decision_lines(decision))

        return "\n".join(lines).rstrip()

    def _format_decision_lines(self, decision: dict[str, Any]) -> list[str]:
        lines = [
            f"- {decision.get('id', 'UNKNOWN')} [{decision.get('status', 'UNKNOWN')}]",
            f"  title: {decision.get('title', '')}",
            f"  date: {decision.get('date', '')}",
        ]

        if decision.get("status") == "APPROVED":
            lines.append(f"  rationale: {decision.get('rationale', '')}")
            files = decision.get("affected_files", []) or []
            if files:
                lines.append(f"  affected_files: {', '.join(files)}")
        else:
            lines.append(f"  rejection_reason: {decision.get('rejection_reason', '')}")

        return lines

    def _terms(self, query: str) -> list[str]:
        cleaned = query.replace("_", " ").replace("-", " ").replace("/", " ")
        stopwords = {
            "add",
            "build",
            "create",
            "improve",
            "update",
            "work",
            "layer",
            "memory",
            "source",
            "grounded",
            "card",
            "cards",
            "for",
            "proposal",
            "proposals",
            "supervised",
            "weebo",
        }
        return [term.lower() for term in cleaned.split() if term and term.lower() not in stopwords]

    def _search_blob(self, decision: dict[str, Any]) -> str:
        parts = [
            decision.get("id", ""),
            decision.get("title", ""),
            decision.get("date", ""),
            decision.get("rationale", ""),
            decision.get("rejection_reason", ""),
            decision.get("status", ""),
            " ".join(decision.get("affected_files", []) or []),
        ]
        return " ".join(str(part) for part in parts).lower().replace("_", " ").replace("-", " ")

    def _clean_scalar(self, value: str) -> str:
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        return value


def _default_memory() -> DecisionMemory:
    return DecisionMemory()


def list_approved() -> list[dict[str, Any]]:
    return _default_memory().list_approved()


def list_rejected() -> list[dict[str, Any]]:
    return _default_memory().list_rejected()


def search_decisions(query: str) -> list[dict[str, Any]]:
    return _default_memory().search_decisions(query)


def already_decided(query: str) -> dict[str, Any]:
    return _default_memory().already_decided(query)
