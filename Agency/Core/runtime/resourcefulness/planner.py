from __future__ import annotations

from typing import Any

from .reconstruct import ReconstructStrategy
from .strategy import ResourcefulnessContext, ResourcefulnessResult, ResourcefulnessStrategy


ENGINEERING_CATEGORY_ORDER = [
    "route_ownership",
    "workspace_host",
    "workbench_root",
    "creation_lifecycle",
    "cleanup_lifecycle",
    "expected_modified_files",
    "verification_surfaces",
]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _category_sort_key(category: str) -> tuple[int, str]:
    try:
        index = ENGINEERING_CATEGORY_ORDER.index(category)
    except ValueError:
        index = len(ENGINEERING_CATEGORY_ORDER)
    return (index, category)


def _path_priority(category: str, path_item: dict[str, Any]) -> tuple[int, int, int, str]:
    path = str(path_item.get("path") or "")
    lower_path = path.lower()
    signals = {str(item).lower() for item in _list(path_item.get("signals"))}
    observations = [
        item for item in _list(path_item.get("observations"))
        if isinstance(item, (str, dict))
    ]
    observation_kinds = {
        str(item.get("kind") or "").lower()
        for item in observations
        if isinstance(item, dict)
    }
    all_signals = signals | observation_kinds

    structural_rank = 3
    if "dependency" in all_signals:
        structural_rank = 0
    elif "symbol" in all_signals:
        structural_rank = 1
    elif "file_inspected" in all_signals:
        structural_rank = 2

    category_markers = {
        "route_ownership": ("main.gd", "project.godot", "route", "router"),
        "workspace_host": ("workspace", "operatorshell/main.gd", "tab"),
        "workbench_root": ("workbench/main", "workbench.gd", "workbenchshellbuilder"),
        "creation_lifecycle": ("main.gd", "session", "controller", "create", "init"),
        "cleanup_lifecycle": ("cleanup", "dispose", "queue_free", "remove", "close"),
        "expected_modified_files": ("main.gd", "workspace", "workbench"),
        "verification_surfaces": ("test", "audit", "verify", "screenshot", "visual"),
    }
    marker_rank = 1
    if any(marker in lower_path for marker in category_markers.get(category, ())):
        marker_rank = 0

    support_rank = 0
    support_markers = ("/audit/", "/output/", "generated", "installer", "install-", ".md", ".json")
    if any(marker in lower_path for marker in support_markers):
        support_rank = 1

    return (support_rank, marker_rank, structural_rank, path)


def _ordered_categories(architecture: dict[str, Any]) -> list[str]:
    return sorted((str(category) for category in architecture), key=_category_sort_key)


def _ordered_paths(category: str, raw_paths: list[Any]) -> list[dict[str, Any]]:
    paths = [item for item in raw_paths if isinstance(item, dict) and item.get("path")]
    return sorted(paths, key=lambda item: _path_priority(category, item))


def _compact_observation_ids(observations: Any, *, limit: int) -> list[str]:
    ids: list[str] = []
    for obs in _list(observations):
        if isinstance(obs, dict):
            observation_id = obs.get("observation_id")
        else:
            observation_id = obs
        if observation_id and observation_id not in ids:
            ids.append(str(observation_id))
        if len(ids) >= limit:
            break
    return ids


def _compact_path(
    raw_path: dict[str, Any],
    *,
    max_signals_per_path: int,
    max_observations_per_path: int,
) -> dict[str, Any]:
    path: dict[str, Any] = {"path": raw_path.get("path")}
    signals = [str(item) for item in _list(raw_path.get("signals")) if str(item).strip()]
    if max_signals_per_path > 0 and signals:
        path["signals"] = sorted(set(signals))[:max_signals_per_path]
    observations = _compact_observation_ids(raw_path.get("observations"), limit=max_observations_per_path)
    if observations:
        path["observations"] = observations
    reason = str(raw_path.get("reason") or "").strip()
    if reason and max_observations_per_path > 1:
        path["reason"] = reason[:120]
    return path


def _count_category_paths(contexts: list[dict[str, Any]]) -> tuple[int, int, set[str], set[str]]:
    categories: set[str] = set()
    paths: set[str] = set()
    for context in contexts:
        for category in _list(context.get("categories")):
            if not isinstance(category, dict):
                continue
            category_name = str(category.get("category") or "")
            if category_name:
                categories.add(category_name)
            for path_item in _list(category.get("paths")):
                if isinstance(path_item, dict) and path_item.get("path"):
                    paths.add(str(path_item.get("path")))
    return (len(categories), len(paths), categories, paths)


def _ordered_relationships(value: Any) -> list[Any]:
    relationships = [item for item in _list(value) if isinstance(item, dict)]
    return sorted(
        relationships,
        key=lambda item: (
            str(item.get("source") or item.get("file") or ""),
            str(item.get("target") or ""),
            int(item.get("pass") or 0),
            str(item.get("observation_id") or item.get("id") or ""),
        ),
    )


class ResourcefulnessPlanner:
    def __init__(self, strategies: list[ResourcefulnessStrategy] | None = None) -> None:
        self._strategies = strategies or [ReconstructStrategy()]

    def select_strategy(self, context: ResourcefulnessContext) -> ResourcefulnessStrategy | None:
        for strategy in self._strategies:
            if strategy.can_execute(context):
                return strategy
        return None

    def run(self, context: ResourcefulnessContext) -> ResourcefulnessResult:
        strategy = self.select_strategy(context)
        if strategy is None:
            return ResourcefulnessResult(
                strategy="none",
                status="resourcefulness_no_strategy",
                reason="No bounded Resourcefulness strategy can execute for this mission state.",
                artifacts={},
                confidence="low",
                next_recommendation="operator_scope_expansion",
            )
        return strategy.execute(context)


def default_planner() -> ResourcefulnessPlanner:
    return ResourcefulnessPlanner()


def compact_resourcefulness_context(
    artifacts: dict[str, Any],
    *,
    max_artifacts: int = 2,
    max_categories: int = 7,
    max_paths_per_category: int = 2,
    max_signals_per_path: int = 4,
    max_observations_per_path: int = 3,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    del max_categories
    for item in artifacts.get("knowledge", [])[-max_artifacts:]:
        if not isinstance(item, dict):
            continue
        data = item.get("data")
        if not isinstance(data, dict) or data.get("strategy") != "reconstruct":
            continue
        architecture = data.get("architecture_evidence", {})
        if not isinstance(architecture, dict):
            architecture = {}
        categories: list[dict[str, Any]] = []
        for category in _ordered_categories(architecture):
            category_data = architecture.get(category, {})
            if not isinstance(category_data, dict):
                continue
            paths: list[dict[str, Any]] = []
            raw_paths = category_data.get("paths", [])
            if isinstance(raw_paths, list):
                for raw_path in _ordered_paths(category, raw_paths)[:max_paths_per_category]:
                    paths.append(_compact_path(
                        raw_path,
                        max_signals_per_path=max_signals_per_path,
                        max_observations_per_path=max_observations_per_path,
                    ))
            if paths:
                categories.append({
                    "category": category,
                    "status": category_data.get("status"),
                    "paths": paths,
                })
        contexts.append({
            "path": item.get("path"),
            "strategy": "reconstruct",
            "diagnosis": data.get("diagnosis", {}),
            "categories": categories,
            "relationships": _ordered_relationships(data.get("relationships", []))[:8],
            "unresolved": data.get("unresolved", [])[:6]
            if isinstance(data.get("unresolved", []), list) else [],
        })
    return contexts

def trim_resourcefulness_context_for_prompt(
    contexts: list[dict[str, Any]],
    *,
    max_artifacts: int = 1,
    max_categories: int = 7,
    max_paths_per_category: int = 2,
    max_relationships: int = 8,
    max_unresolved: int = 6,
    max_signals_per_path: int = 4,
    max_observations_per_path: int = 3,
) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    del max_categories
    for raw in contexts[:max_artifacts]:
        if not isinstance(raw, dict):
            continue
        categories: list[dict[str, Any]] = []
        raw_categories = [
            item for item in _list(raw.get("categories"))
            if isinstance(item, dict) and item.get("category")
        ]
        raw_categories = sorted(
            raw_categories,
            key=lambda item: _category_sort_key(str(item.get("category") or "")),
        )
        for category in raw_categories:
            category_name = str(category.get("category") or "")
            paths: list[dict[str, Any]] = []
            for path_item in _ordered_paths(category_name, _list(category.get("paths")))[:max_paths_per_category]:
                paths.append(_compact_path(
                    path_item,
                    max_signals_per_path=max_signals_per_path,
                    max_observations_per_path=max_observations_per_path,
                ))
            if paths:
                categories.append({
                    "category": category_name,
                    "status": category.get("status"),
                    "paths": paths,
                })
        diagnosis = raw.get("diagnosis", {}) if isinstance(raw.get("diagnosis"), dict) else {}
        trimmed.append({
            "strategy": raw.get("strategy"),
            "diagnosis": {
                "reason": str(diagnosis.get("reason") or "")[:180],
                "inspection_passes": diagnosis.get("inspection_passes"),
                "files_inspected": diagnosis.get("files_inspected"),
            },
            "categories": categories,
            "relationships": _ordered_relationships(raw.get("relationships", []))[:max_relationships],
            "unresolved": raw.get("unresolved", [])[:max_unresolved]
            if isinstance(raw.get("unresolved", []), list) else [],
        })
    return trimmed


def resourcefulness_compression_diagnostics(
    original_contexts: list[dict[str, Any]],
    retained_contexts: list[dict[str, Any]],
    *,
    final_prompt_size: int,
    configured_budget: int,
) -> dict[str, Any]:
    original_category_count, original_path_count, _original_categories, original_paths = (
        _count_category_paths(original_contexts)
    )
    retained_category_count, retained_path_count, _retained_categories, retained_paths = (
        _count_category_paths(retained_contexts)
    )
    original_relationships = [
        relationship
        for context in original_contexts
        for relationship in _list(context.get("relationships"))
    ]
    retained_relationship_keys = {
        repr(relationship)
        for context in retained_contexts
        for relationship in _list(context.get("relationships"))
    }
    dropped_relationships = [
        relationship
        for relationship in original_relationships
        if repr(relationship) not in retained_relationship_keys
    ]
    return {
        "original_category_count": original_category_count,
        "retained_category_count": retained_category_count,
        "original_path_count": original_path_count,
        "retained_path_count": retained_path_count,
        "dropped_paths": sorted(original_paths - retained_paths),
        "dropped_relationships": dropped_relationships,
        "final_prompt_size": final_prompt_size,
        "configured_budget": configured_budget,
    }
