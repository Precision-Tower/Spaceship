from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.foundation.paths import AGENCY_ROOT, INSPECTIONS_ROOT, DASHBOARD_ROOT, stable_path

SUPPORTED_TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".toml", ".md", ".txt", ".sh"}
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".gz",
    ".tar", ".7z", ".rar", ".db", ".sqlite", ".sqlite3", ".pyc", ".pyo",
    ".so", ".dll", ".exe", ".bin", ".gguf", ".onnx", ".pt", ".safetensors",
}
DEFAULT_EXCLUDES = (
    ".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv",
    "*_env", "Chroma", "memory/Chroma", "build", "dist", ".godot",
    "logs", "sessions", "*.pyc", "*.pyo", "*.sqlite", "*.sqlite3", "*.db",
    ".env", ".env.*", "*.pem", "*.key", "*token*", "*credential*", "*secret*",
)
DEFAULT_LIMITS = {
    "max_files": 500,
    "max_matches": 500,
    "max_file_bytes": 120_000,
    "max_depth": 2,
    "max_total_context_bytes": 40_000,
    "max_evidence_items": 500,
}
DEFAULT_OPERATIONS = ("path_discovery", "text_search", "symbol_definition", "imports", "references")
OPERATION_ALIASES = {
    "path": "path_discovery",
    "paths": "path_discovery",
    "discover": "path_discovery",
    "discovery": "path_discovery",
    "search": "text_search",
    "text": "text_search",
    "grep": "text_search",
    "definition": "symbol_definition",
    "definitions": "symbol_definition",
    "symbol": "symbol_definition",
    "symbols": "symbol_definition",
    "import": "imports",
    "caller": "references",
    "callers": "references",
    "reference": "references",
    "dependency": "dependency_trace",
    "dependencies": "dependency_trace",
    "trace": "dependency_trace",
}
WORK_INSPECTIONS_ROOT = INSPECTIONS_ROOT
REQUEST_DOC_RE = re.compile(r"\bRepositoryContextRequest\b\s*:", re.IGNORECASE)
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:Agency|UI|Engineering|Tools|local)(?:/[A-Za-z0-9_.@+-]+)+|run\.py)"
    r"(?![A-Za-z0-9_./-])"
)
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")


@dataclass(frozen=True)
class RepositoryContextRequest:
    request_id: str
    objective: str
    include: list[str]
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    operations: list[str] = field(default_factory=lambda: list(DEFAULT_OPERATIONS))
    symbols: list[str] = field(default_factory=list)
    text: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    limits: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_LIMITS))
    output: list[str] = field(default_factory=lambda: ["evidence_bundle"])
    constraints: list[str] = field(default_factory=lambda: ["read_only", "preserve_unknowns", "require_line_citations"])
    synthesis: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    request_id: str
    status: str
    objective: str
    repository_root: str
    repository_root_authority: str
    effective_scope: dict[str, Any]
    operations_performed: list[str]
    findings: list[dict[str, Any]]
    symbols: list[dict[str, Any]]
    references: list[dict[str, Any]]
    imports: list[dict[str, Any]]
    dependency_edges: list[dict[str, Any]]
    negative_results: list[dict[str, Any]]
    files_examined: list[str]
    files_skipped: list[dict[str, Any]]
    limits: dict[str, Any]
    parse_failures: list[dict[str, Any]]
    unresolveds: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    generated_at: str
    persistence_path: str | None = None
    repository_mutation_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"EvidenceBundle": asdict(self)}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repository_root() -> Path:
    return DASHBOARD_ROOT.resolve()


def _request_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"repoctx-{digest}"


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _merge_limits(limits: dict[str, Any] | None) -> dict[str, int]:
    merged = dict(DEFAULT_LIMITS)
    for key, value in (limits or {}).items():
        if key in merged:
            try:
                merged[key] = max(0, int(value))
            except (TypeError, ValueError):
                pass
    return merged


def _normalize_operations(values: Iterable[Any]) -> list[str]:
    operations: list[str] = []
    for value in values:
        key = str(value).strip()
        if not key:
            continue
        normalized = OPERATION_ALIASES.get(key.lower(), key)
        if normalized not in operations:
            operations.append(normalized)
    return operations


def request_from_mapping(data: dict[str, Any]) -> RepositoryContextRequest:
    root = data.get("RepositoryContextRequest", data)
    if not isinstance(root, dict):
        raise ValueError("invalid_repository_context_request")
    scope = root.get("scope") if isinstance(root.get("scope"), dict) else {}
    query = root.get("query") if isinstance(root.get("query"), dict) else {}
    output = root.get("output")
    if isinstance(output, dict):
        output_list = [key for key, enabled in output.items() if enabled]
    else:
        output_list = _coerce_list(output) or ["evidence_bundle"]
    include = _coerce_list(scope.get("include") or root.get("include"))
    seed = json.dumps(root, sort_keys=True, default=str)
    return RepositoryContextRequest(
        request_id=str(root.get("request_id") or _request_id(seed)),
        objective=str(root.get("objective") or "Repository inspection").strip(),
        include=include,
        exclude=_coerce_list(scope.get("exclude") or root.get("exclude")) or list(DEFAULT_EXCLUDES),
        operations=_normalize_operations(_coerce_list(root.get("operations")) or list(DEFAULT_OPERATIONS)),
        symbols=_coerce_list(query.get("symbols") or root.get("symbols")),
        text=_coerce_list(query.get("text") or root.get("text")),
        paths=_coerce_list(query.get("paths") or root.get("paths")),
        limits=_merge_limits(root.get("limits") if isinstance(root.get("limits"), dict) else None),
        output=output_list,
        constraints=_coerce_list(root.get("constraints")) or ["read_only", "preserve_unknowns", "require_line_citations"],
        synthesis=bool(root.get("synthesis") or "synthesis" in output_list),
    )


def parse_repository_context_request(text: str) -> RepositoryContextRequest | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    data: Any = None
    if REQUEST_DOC_RE.search(raw) or raw.startswith("{"):
        try:
            data = yaml.safe_load(raw)
        except Exception:
            data = None
    if isinstance(data, dict):
        return request_from_mapping(data)
    return natural_language_request(raw)


def classify_repository_inspection_request(text: str) -> bool:
    return parse_repository_context_request(text) is not None


def _named_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in PATH_RE.finditer(text):
        value = match.group(1).strip().rstrip(".,;:")
        if value not in paths:
            paths.append(value)
    return paths


def _symbol_candidates(text: str) -> list[str]:
    stop = {
        "please", "inspect", "agency", "core", "runtime", "trace", "find",
        "definition", "definitions", "references", "callers", "imports",
        "search", "show", "direct", "for", "the", "and", "in", "of", "path",
        "environment", "dependencies", "dependency", "depth", "whether",
        "exists", "determine", "legacy",
    }
    found: list[str] = []
    for item in IDENT_RE.findall(text):
        if item.lower() in stop:
            continue
        if item not in found:
            found.append(item)
    return found[:12]


def _text_queries(text: str, symbols: list[str]) -> list[str]:
    lowered = text.lower()
    queries: list[str] = []
    if "search" in lowered and " for " in lowered:
        tail = text[lowered.rfind(" for ") + 5:]
        tail = re.split(r"\s+(?:in|under|within)\s+", tail, maxsplit=1, flags=re.IGNORECASE)[0]
        tail = tail.strip(" .,:;'\"")
        if tail and "/" not in tail:
            queries.append(tail)
    if "environment runtime" in lowered:
        queries.extend(["EnvironmentManifest", "environment", "runtime"])
    for symbol in symbols:
        if symbol not in queries:
            queries.append(symbol)
    return queries[:12]


def natural_language_request(text: str) -> RepositoryContextRequest | None:
    lowered = text.lower()
    operation_words = (
        "inspect", "find", "trace", "search", "locate", "callers", "caller",
        "imports", "definitions", "definition", "references", "reference",
        "dependency", "dependencies",
    )
    if not any(word in lowered for word in operation_words):
        return None
    include = _named_paths(text)
    if not include:
        if "repository-wide" in lowered or "entire repository" in lowered or "whole repository" in lowered:
            include = ["."]
        else:
            return None
    operations: list[str] = []
    if "inspect" in lowered:
        operations.append("path_discovery")
    if any(word in lowered for word in ("search", "find", "locate", "inspect", "trace")):
        operations.append("text_search")
    if any(word in lowered for word in ("definition", "definitions", "symbol", "exists")):
        operations.append("symbol_definition")
    if "import" in lowered or "dependenc" in lowered or "trace" in lowered:
        operations.extend(["imports", "dependency_trace"])
    if any(word in lowered for word in ("reference", "references", "caller", "callers", "trace", "dependenc")):
        operations.append("references")
    symbols = _symbol_candidates(text)
    queries = _text_queries(text, symbols)
    limits = dict(DEFAULT_LIMITS)
    depth_match = re.search(r"\bdepth\s+(\d+)\b", lowered)
    if depth_match:
        limits["max_depth"] = int(depth_match.group(1))
    seen_ops = []
    for op in operations:
        if op not in seen_ops:
            seen_ops.append(op)
    return RepositoryContextRequest(
        request_id=_request_id(text),
        objective=text.strip(),
        include=include,
        operations=seen_ops,
        symbols=symbols,
        text=queries,
        paths=include,
        limits=limits,
    )


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _pattern_matches(path: Path, pattern: str, rel: str) -> bool:
    import fnmatch

    value = str(pattern).strip()
    if not value:
        return False
    if any(char in value for char in "*?[]"):
        return fnmatch.fnmatch(path.name, value) or fnmatch.fnmatch(rel, value)
    if "/" in value:
        normalized = value.strip("/")
        return rel == normalized or rel.startswith(normalized + "/") or ("/" + normalized + "/") in ("/" + rel + "/")
    return value in set(path.parts) | set(Path(rel).parts) or path.name == value


def _excluded(path: Path, root: Path, patterns: Iterable[str]) -> str | None:
    rel = _safe_relative(path, root)
    for pattern in patterns:
        if _pattern_matches(path, pattern, rel):
            lowered = pattern.lower()
            if (
                "token" in lowered or "credential" in lowered or "secret" in lowered
                or pattern.startswith(".env") or pattern.endswith(".key") or pattern.endswith(".pem")
            ):
                return "sensitive_path_excluded"
            return f"excluded_by_pattern:{pattern}"
    return None


def _resolve_scope_path(value: str, root: Path) -> Path:
    raw = Path(str(value).strip())
    if ".." in raw.parts:
        raise ValueError(f"path_traversal_rejected: {value}")
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve()
    if not _is_relative_to(resolved, root):
        raise ValueError(f"path_escapes_repository_root: {value}")
    if not resolved.exists():
        raise ValueError(f"path_not_found: {value}")
    mode = resolved.stat().st_mode
    if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise ValueError(f"special_file_rejected: {value}")
    return resolved


def _looks_binary(path: Path, max_bytes: int) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[: min(max_bytes, 4096)]
    except OSError:
        return True
    return b"\0" in sample


def _read_text(path: Path, max_file_bytes: int) -> tuple[str | None, str | None]:
    if _looks_binary(path, max_file_bytes):
        return None, "binary_file_skipped"
    if path.stat().st_size > max_file_bytes:
        return None, "max_file_bytes_exceeded"
    try:
        return path.read_text(encoding="utf-8-sig"), None
    except UnicodeDecodeError:
        return None, "unicode_decode_failed"
    except OSError as exc:
        return None, f"read_failed:{type(exc).__name__}"


def _scope_files(request: RepositoryContextRequest, root: Path) -> tuple[list[Path], list[dict[str, Any]], list[str], dict[str, bool]]:
    files: list[Path] = []
    skipped: list[dict[str, Any]] = []
    include_rels: list[str] = []
    limits_reached = {"max_files": False}
    max_files = request.limits.get("max_files", DEFAULT_LIMITS["max_files"])
    for include in request.include:
        resolved = _resolve_scope_path(include, root)
        include_rels.append(_safe_relative(resolved, root))
        candidates = [resolved] if resolved.is_file() else sorted(resolved.rglob("*"), key=lambda p: _safe_relative(p, root))
        for candidate in candidates:
            rel = _safe_relative(candidate, root)
            if candidate.is_dir():
                continue
            if candidate.is_symlink() and not _is_relative_to(candidate.resolve(), root):
                skipped.append({"path": rel, "reason": "symlink_escape_rejected"})
                continue
            if not candidate.is_file():
                skipped.append({"path": rel, "reason": "special_or_non_file_skipped"})
                continue
            reason = _excluded(candidate, root, request.exclude)
            if reason:
                skipped.append({"path": rel, "reason": reason})
                continue
            if len(files) >= max_files:
                limits_reached["max_files"] = True
                return files, skipped, include_rels, limits_reached
            files.append(candidate)
    return files, skipped, include_rels, limits_reached


def _line_excerpt(lines: list[str], start: int, end: int | None = None) -> str:
    end = end or start
    return "\n".join(lines[max(start - 1, 0): max(end, start)]).rstrip("\n")


def _finding(fid: int, claim: str, evidence: dict[str, Any], classification: str = "confirmed", confidence: str = "high") -> dict[str, Any]:
    return {"id": f"finding-{fid:03d}", "claim": claim, "classification": classification, "confidence": confidence, "evidence": [evidence]}


class _PythonAnalyzer(ast.NodeVisitor):
    def __init__(self, rel: str, lines: list[str], symbols: set[str]):
        self.rel = rel
        self.lines = lines
        self.symbol_filter = symbols
        self.stack: list[str] = []
        self.definitions: list[dict[str, Any]] = []
        self.imports: list[dict[str, Any]] = []
        self.references: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []

    def _wanted(self, name: str) -> bool:
        return not self.symbol_filter or name in self.symbol_filter or name.split(".")[-1] in self.symbol_filter

    def _qual(self, name: str) -> str:
        return ".".join(self.stack + [name]) if self.stack else name

    def _evidence(self, node: ast.AST, evidence_type: str, end: int | None = None) -> dict[str, Any]:
        start = getattr(node, "lineno", 1)
        end_line = end or getattr(node, "end_lineno", start)
        return {
            "path": self.rel,
            "start_line": start,
            "end_line": end_line,
            "excerpt": _line_excerpt(self.lines, start, end_line),
            "evidence_type": evidence_type,
        }

    def _add_def(self, node: ast.AST, name: str, kind: str) -> None:
        qualified = self._qual(name)
        if self._wanted(name) or self._wanted(qualified):
            ev = self._evidence(node, "symbol_definition")
            self.definitions.append({
                "symbol": name,
                "qualified_name": qualified,
                "path": self.rel,
                "start_line": ev["start_line"],
                "end_line": ev["end_line"],
                "definition_kind": kind,
                "evidence": ev,
                "classification": "confirmed",
                "confidence": "high",
            })
            self.edges.append({
                "source": self.rel,
                "target": qualified,
                "relationship_type": "defines",
                "path": self.rel,
                "line": ev["start_line"],
                "confidence": "confirmed",
                "depth": 1,
                "evidence": ev,
            })

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._add_def(node, node.name, "function")
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._add_def(node, node.name, "async_function")
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._add_def(node, node.name, "class")
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Assign(self, node: ast.Assign) -> Any:
        if not self.stack:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._add_def(node, target.id, "top_level_assignment")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if not self.stack and isinstance(node.target, ast.Name):
            self._add_def(node, node.target.id, "top_level_assignment")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        names = [{"name": alias.name, "alias": alias.asname} for alias in node.names]
        ev = self._evidence(node, "import")
        self.imports.append({"path": self.rel, "module": None, "imported_names": names, "line": ev["start_line"], "relative": False, "evidence": ev})
        for item in names:
            self.edges.append({"source": self.rel, "target": item["name"], "relationship_type": "imports", "path": self.rel, "line": ev["start_line"], "confidence": "confirmed", "depth": 1, "evidence": ev})

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        names = [{"name": alias.name, "alias": alias.asname} for alias in node.names]
        ev = self._evidence(node, "import")
        module = "." * int(node.level or 0) + str(node.module or "")
        self.imports.append({"path": self.rel, "module": module, "imported_names": names, "line": ev["start_line"], "relative": bool(node.level), "evidence": ev})
        for item in names:
            self.edges.append({"source": self.rel, "target": f"{module}.{item['name']}".strip("."), "relationship_type": "imports_from", "path": self.rel, "line": ev["start_line"], "confidence": "confirmed", "depth": 1, "evidence": ev})

    def visit_Name(self, node: ast.Name) -> Any:
        if self._wanted(node.id):
            ev = self._evidence(node, "syntactic_reference")
            context = self._qual("").strip(".")
            self.references.append({"symbol": node.id, "path": self.rel, "line": ev["start_line"], "reference_type": "syntactic_reference", "context": context, "evidence": ev, "classification": "confirmed", "confidence": "medium"})
            self.edges.append({"source": context or self.rel, "target": node.id, "relationship_type": "references", "path": self.rel, "line": ev["start_line"], "confidence": "weakly_inferred", "depth": 1, "evidence": ev})
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if self._wanted(node.attr):
            ev = self._evidence(node, "attribute_reference")
            self.references.append({"symbol": node.attr, "path": self.rel, "line": ev["start_line"], "reference_type": "syntactic_reference", "context": self._qual("").strip("."), "evidence": ev, "classification": "confirmed", "confidence": "medium"})
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        target = None
        if isinstance(node.func, ast.Name):
            target = node.func.id
        elif isinstance(node.func, ast.Attribute):
            target = node.func.attr
        if target and self._wanted(target):
            ev = self._evidence(node, "call_site", getattr(node.func, "end_lineno", getattr(node, "lineno", 1)))
            context = self._qual("").strip(".")
            self.references.append({"symbol": target, "path": self.rel, "line": ev["start_line"], "reference_type": "possible_call_site", "context": context, "evidence": ev, "classification": "strongly_inferred", "confidence": "medium"})
            self.edges.append({"source": context or self.rel, "target": target, "relationship_type": "calls_directly", "path": self.rel, "line": ev["start_line"], "confidence": "strongly_inferred", "depth": 1, "evidence": ev})
        self.generic_visit(node)


def _collect_path_findings(paths: list[Path], root: Path, query_paths: list[str], max_items: int) -> list[dict[str, Any]]:
    findings = []
    wanted = [Path(item).name.lower() for item in query_paths if item]
    for path in paths:
        rel = _safe_relative(path, root)
        if wanted and not any(item in rel.lower() or item == path.name.lower() for item in wanted):
            continue
        findings.append({"path": rel, "match_type": "path", "query": query_paths or ["scope"], "classification": "confirmed", "confidence": "high"})
        if len(findings) >= max_items:
            break
    return findings


def _rejected_bundle(request: RepositoryContextRequest, reason: str) -> EvidenceBundle:
    return EvidenceBundle(
        request_id=request.request_id,
        status="rejected",
        objective=request.objective,
        repository_root=str(repository_root()),
        repository_root_authority="Agency.Core.foundation.paths.DASHBOARD_ROOT",
        effective_scope={"include": request.include, "exclude": request.exclude, "default_exclusions": list(DEFAULT_EXCLUDES)},
        operations_performed=[],
        findings=[],
        symbols=[],
        references=[],
        imports=[],
        dependency_edges=[],
        negative_results=[],
        files_examined=[],
        files_skipped=[],
        limits={"configured": dict(request.limits), "reached": {key: False for key in request.limits}},
        parse_failures=[],
        unresolveds=[{"reason": reason, "classification": "unresolved"}],
        contradictions=[],
        generated_at=_now(),
    )


def build_repository_context(request: RepositoryContextRequest, *, persist: bool = True) -> EvidenceBundle:
    root = repository_root()
    configured_limits = dict(request.limits)
    reached = {key: False for key in configured_limits}
    findings: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    negative: list[dict[str, Any]] = []
    parse_failures: list[dict[str, Any]] = []
    unresolveds: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    files_examined: list[str] = []
    skipped: list[dict[str, Any]] = []
    total_excerpt_bytes = 0
    finding_id = 1

    if not request.include:
        bundle = _rejected_bundle(request, "explicit_scope_required")
        return _persist_bundle(request, bundle) if persist else bundle

    try:
        files, skipped, include_rels, scope_limits = _scope_files(request, root)
    except ValueError as exc:
        bundle = _rejected_bundle(request, str(exc))
        return _persist_bundle(request, bundle) if persist else bundle

    reached.update(scope_limits)
    operations = _normalize_operations(request.operations)
    max_matches = configured_limits.get("max_matches", DEFAULT_LIMITS["max_matches"])
    max_evidence = configured_limits.get("max_evidence_items", DEFAULT_LIMITS["max_evidence_items"])
    max_total = configured_limits.get("max_total_context_bytes", DEFAULT_LIMITS["max_total_context_bytes"])
    max_depth = configured_limits.get("max_depth", DEFAULT_LIMITS["max_depth"])
    symbol_filter = set(request.symbols)
    text_queries = [item for item in request.text if item]

    if "path_discovery" in operations:
        for item in _collect_path_findings(files, root, request.paths or request.include, max_evidence):
            evidence = {
                "path": item["path"],
                "start_line": 1,
                "end_line": 1,
                "excerpt": item["path"],
                "evidence_type": "path_discovery",
            }
            findings.append(_finding(finding_id, f"Path matched within scope: {item['path']}", evidence))
            finding_id += 1

    for path in files:
        rel = _safe_relative(path, root)
        text, skip_reason = _read_text(path, configured_limits.get("max_file_bytes", DEFAULT_LIMITS["max_file_bytes"]))
        if skip_reason:
            skipped.append({"path": rel, "reason": skip_reason})
            continue
        assert text is not None
        files_examined.append(rel)
        lines = text.splitlines()

        if "text_search" in operations and text_queries:
            for query in text_queries:
                lowered_query = query.lower()
                for index, line in enumerate(lines, start=1):
                    if lowered_query in line.lower():
                        excerpt = line.rstrip("\n")
                        total_excerpt_bytes += len(excerpt.encode("utf-8", errors="replace"))
                        evidence = {
                            "path": rel,
                            "start_line": index,
                            "end_line": index,
                            "excerpt": excerpt,
                            "evidence_type": "text_search",
                            "query": query,
                            "match_type": "exact_text",
                        }
                        findings.append(_finding(finding_id, f"Text query '{query}' matched {rel}:{index}.", evidence))
                        finding_id += 1
                        if len(findings) >= max_matches:
                            reached["max_matches"] = True
                            break
                        if total_excerpt_bytes >= max_total:
                            reached["max_total_context_bytes"] = True
                            break
                if reached.get("max_matches") or reached.get("max_total_context_bytes"):
                    break

        if path.suffix.lower() == ".py" and any(op in operations for op in ("symbol_definition", "imports", "references", "dependency_trace")):
            try:
                tree = ast.parse(text, filename=rel)
            except SyntaxError as exc:
                parse_failures.append({"path": rel, "line": exc.lineno, "reason": exc.msg})
                continue
            analyzer = _PythonAnalyzer(rel, lines, symbol_filter)
            analyzer.visit(tree)
            if "symbol_definition" in operations:
                symbols.extend(analyzer.definitions)
                for definition in analyzer.definitions:
                    findings.append(_finding(finding_id, f"Symbol '{definition['qualified_name']}' is defined in {rel}:{definition['start_line']}.", definition["evidence"]))
                    finding_id += 1
            if "imports" in operations:
                imports.extend(analyzer.imports)
            if "references" in operations:
                references.extend(analyzer.references)
            if "dependency_trace" in operations:
                for edge in analyzer.edges:
                    if int(edge.get("depth", 1)) <= max_depth:
                        edges.append(edge)

        if reached.get("max_matches") or reached.get("max_total_context_bytes") or len(findings) >= max_evidence:
            if len(findings) >= max_evidence:
                reached["max_evidence_items"] = True
            break

    if request.symbols and "symbol_definition" in operations:
        found = {item.get("symbol") for item in symbols} | {item.get("qualified_name") for item in symbols}
        for symbol in request.symbols:
            if symbol not in found:
                negative.append({
                    "query": symbol,
                    "result": "not_found_within_scope",
                    "search_method": "python_ast_symbol_definition",
                    "classification": "not_found_within_scope",
                    "searched_scope": include_rels,
                })
    if text_queries and "text_search" in operations:
        found_queries = {
            item["evidence"][0].get("query")
            for item in findings
            if item.get("evidence") and item["evidence"][0].get("evidence_type") == "text_search"
        }
        for query in text_queries:
            if query not in found_queries:
                negative.append({
                    "query": query,
                    "result": "not_found_within_scope",
                    "search_method": "bounded_text_search",
                    "classification": "not_found_within_scope",
                    "searched_scope": include_rels,
                })

    status = "partial" if any(reached.values()) else "completed"
    bundle = EvidenceBundle(
        request_id=request.request_id,
        status=status,
        objective=request.objective,
        repository_root=str(root),
        repository_root_authority="Agency.Core.foundation.paths.DASHBOARD_ROOT",
        effective_scope={"include": include_rels, "exclude": request.exclude, "default_exclusions": list(DEFAULT_EXCLUDES)},
        operations_performed=operations,
        findings=findings[:max_evidence],
        symbols=symbols[:max_evidence],
        references=references[:max_evidence],
        imports=imports[:max_evidence],
        dependency_edges=edges[:max_evidence],
        negative_results=negative,
        files_examined=files_examined,
        files_skipped=skipped,
        limits={"configured": configured_limits, "reached": reached},
        parse_failures=parse_failures,
        unresolveds=unresolveds,
        contradictions=contradictions,
        generated_at=_now(),
    )
    return _persist_bundle(request, bundle) if persist else bundle


def _persist_bundle(request: RepositoryContextRequest, bundle: EvidenceBundle) -> EvidenceBundle:
    target = WORK_INSPECTIONS_ROOT / request.request_id
    target.mkdir(parents=True, exist_ok=True)
    (target / "request.yaml").write_text(
        yaml.safe_dump({"RepositoryContextRequest": request.to_dict()}, sort_keys=False),
        encoding="utf-8",
    )
    payload = bundle.to_dict()
    payload["EvidenceBundle"]["persistence_path"] = stable_path(target)
    (target / "evidence.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    (target / "metadata.yaml").write_text(
        yaml.safe_dump(
            {
                "request_id": request.request_id,
                "status": bundle.status,
                "generated_at": bundle.generated_at,
                "requesting_agent": None,
                "vector_memory_authority": False,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return EvidenceBundle(**payload["EvidenceBundle"])


def load_evidence_bundle(request_id: str) -> EvidenceBundle:
    path = WORK_INSPECTIONS_ROOT / request_id / "evidence.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    root = data.get("EvidenceBundle") if isinstance(data, dict) else {}
    if not isinstance(root, dict):
        raise ValueError(f"invalid_evidence_bundle: {request_id}")
    return EvidenceBundle(**root)


def evidence_summary(bundle: EvidenceBundle, *, max_findings: int = 12) -> str:
    lines = [
        f"Repository inspection: {bundle.status}",
        f"Request: {bundle.request_id}",
        f"Objective: {bundle.objective}",
        f"Scope: {', '.join(bundle.effective_scope.get('include', [])) or 'none'}",
        f"Files examined: {len(bundle.files_examined)}",
        f"Matches/findings: {len(bundle.findings)}",
        f"Repository mutation performed: {str(bundle.repository_mutation_performed).lower()}",
    ]
    reached = [key for key, value in bundle.limits.get("reached", {}).items() if value]
    if reached:
        lines.append(f"Limits reached: {', '.join(reached)}")
    if bundle.findings:
        lines.append("Findings:")
        for item in bundle.findings[:max_findings]:
            evidence = item.get("evidence", [{}])[0]
            lines.append(f"- {item.get('classification')}: {item.get('claim')} [{evidence.get('path')}:{evidence.get('start_line')}]")
    if bundle.symbols:
        lines.append("Symbols:")
        for item in bundle.symbols[:max_findings]:
            lines.append(f"- {item.get('definition_kind')}: {item.get('qualified_name')} at {item.get('path')}:{item.get('start_line')}")
    if bundle.imports:
        lines.append("Imports:")
        for item in bundle.imports[:max_findings]:
            names = ", ".join(name.get("name") for name in item.get("imported_names", []))
            lines.append(f"- {item.get('path')}:{item.get('line')} imports {item.get('module') or names}")
    if bundle.references:
        lines.append("References:")
        for item in bundle.references[:max_findings]:
            lines.append(f"- {item.get('reference_type')}: {item.get('symbol')} at {item.get('path')}:{item.get('line')}")
    if bundle.dependency_edges:
        lines.append("Dependency edges:")
        for item in bundle.dependency_edges[:max_findings]:
            lines.append(f"- {item.get('relationship_type')}: {item.get('source')} -> {item.get('target')} at {item.get('path')}:{item.get('line')} ({item.get('confidence')})")
    if bundle.negative_results:
        lines.append("Negative results:")
        for item in bundle.negative_results[:max_findings]:
            lines.append(f"- {item.get('query')}: {item.get('result')}")
    if bundle.parse_failures:
        lines.append("Parse failures:")
        for item in bundle.parse_failures[:max_findings]:
            lines.append(f"- {item.get('path')}:{item.get('line')} {item.get('reason')}")
    if bundle.files_skipped:
        lines.append("Skipped files:")
        for item in bundle.files_skipped[:max_findings]:
            lines.append(f"- {item.get('path')}: {item.get('reason')}")
    return "\n".join(lines)


def repository_inspection_payload(agent_name: str, prompt: str, *, synthesis: bool | None = None) -> dict[str, Any] | None:
    request = parse_repository_context_request(prompt)
    if request is None:
        return None
    if synthesis is not None:
        request = RepositoryContextRequest(**{**request.to_dict(), "synthesis": synthesis})
    bundle = build_repository_context(request, persist=True)
    draft = evidence_summary(bundle)
    return {
        "ok": bundle.status not in {"rejected", "failed"},
        "status": bundle.status,
        "agent": agent_name,
        "context_route": "repository_inspection",
        "response_provenance": "repository_evidence",
        "draft": draft,
        "answer": draft,
        "response": draft,
        "repository_evidence_loaded": True,
        "evidence_bundle_available": True,
        "evidence_bundle": bundle.to_dict()["EvidenceBundle"],
        "repository_context_request": request.to_dict(),
        "model_synthesis_used": False,
        "files_examined_count": len(bundle.files_examined),
        "matches_count": len(bundle.findings) + len(bundle.symbols) + len(bundle.references),
        "limits_reached": bundle.limits.get("reached", {}),
        "repository_mutation_performed": False,
        "memory_results_loaded": 0,
        "memory_retrieval_skipped": True,
        "direct_file_context_loaded": False,
        "workspace_snapshot_loaded": False,
    }


def inspect_from_args(argv: list[str]) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="python run.py repository inspect")
    parser.add_argument("--agent", default="Agent")
    parser.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--scope", action="append", dest="scopes")
    parser.add_argument("--symbol", action="append", dest="symbols")
    parser.add_argument("--text", action="append", dest="texts")
    parser.add_argument("--operation", action="append", dest="operations")
    parser.add_argument("--max-files", type=int, default=DEFAULT_LIMITS["max_files"])
    parser.add_argument("--max-matches", type=int, default=DEFAULT_LIMITS["max_matches"])
    parsed = parser.parse_args(argv)
    include = parsed.scopes or parsed.paths or []
    request = RepositoryContextRequest(
        request_id=_request_id(json.dumps(vars(parsed), sort_keys=True)),
        objective="CLI repository inspection",
        include=include,
        operations=_normalize_operations(parsed.operations or list(DEFAULT_OPERATIONS)),
        symbols=parsed.symbols or [],
        text=parsed.texts or parsed.symbols or [],
        paths=parsed.paths or include,
        limits={**DEFAULT_LIMITS, "max_files": parsed.max_files, "max_matches": parsed.max_matches},
    )
    bundle = build_repository_context(request, persist=True)
    return {
        "ok": bundle.status not in {"rejected", "failed"},
        "request_id": request.request_id,
        "status": bundle.status,
        "evidence_bundle": bundle.to_dict()["EvidenceBundle"],
        "summary": evidence_summary(bundle),
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or []
    if not argv or argv[0] in {"-h", "--help"}:
        print("usage: python run.py repository inspect --path Agency/Core --symbol authoritative_state --operation symbol_definition")
        return 0 if argv else 2
    command = argv[0]
    if command == "inspect":
        payload = inspect_from_args(argv[1:])
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1
    if command == "status" and len(argv) >= 2:
        bundle = load_evidence_bundle(argv[1])
        print(json.dumps(bundle.to_dict()["EvidenceBundle"], indent=2))
        return 0
    print(f"ERR: unknown repository command: {command}")
    return 2
