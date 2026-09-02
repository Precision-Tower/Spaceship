from __future__ import annotations

from typing import Any


def select_high_value_evidence(
    evidence: dict[str, Any],
    *,
    coverage_categories: tuple[str, ...] | list[str],
    limit: int = 34,
) -> list[dict[str, Any]]:
    priority = {'file_inspected': 0, 'symbol': 1, 'dependency': 2, 'pass_observation': 3}

    def sort_key(item: dict[str, Any]) -> tuple[int, int, str, str]:
        return (priority.get(str(item.get('kind') or ''), 9), int(item.get('pass') or 0), str(item.get('path') or ''), str(item.get('id') or ''))
    observations = sorted([item for item in evidence.get('observations', []) if isinstance(item, dict) and str(item.get('id') or '')], key=sort_key)
    by_path: dict[str, list[dict[str, Any]]] = {}
    by_kind: dict[str, list[dict[str, Any]]] = {'file_inspected': [], 'symbol': [], 'dependency': [], 'pass_observation': []}
    for item in observations:
        kind = str(item.get('kind') or '')
        if kind in by_kind:
            by_kind[kind].append(item)
        path = str(item.get('path') or '')
        if path:
            by_path.setdefault(path, []).append(item)
    coverage_evidence = evidence.get('coverage_evidence', {})
    if not isinstance(coverage_evidence, dict):
        coverage_evidence = {}
    coverage_paths: list[str] = []
    seen_paths: set[str] = set()
    coverage_categories = [*coverage_categories, *sorted((str(category) for category in coverage_evidence if category not in coverage_categories))]
    for category in coverage_categories:
        raw_items = coverage_evidence.get(category, [])
        if not isinstance(raw_items, list):
            continue
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            path = str(raw.get('path') or '').strip()
            if path and path not in seen_paths:
                seen_paths.add(path)
                coverage_paths.append(path)
    coverage_candidates: list[dict[str, Any]] = []
    max_path_observations = max((len(by_path.get(path, [])) for path in coverage_paths), default=0)
    for index in range(max_path_observations):
        for path in coverage_paths:
            path_observations = by_path.get(path, [])
            if index < len(path_observations):
                coverage_candidates.append(path_observations[index])
    max_pass = max((int(item.get('pass') or 0) for item in observations), default=0)
    late_candidates = sorted([item for item in observations if int(item.get('pass') or 0) == max_pass and max_pass > 0], key=sort_key)
    structural_candidates = [*by_kind['symbol'], *by_kind['dependency']]
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def append_candidates(candidates: list[dict[str, Any]], max_items: int) -> int:
        added = 0
        if max_items <= 0:
            return added
        for item in candidates:
            observation_id = str(item.get('id') or '')
            if not observation_id or observation_id in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(observation_id)
            added += 1
            if len(selected) >= limit or added >= max_items:
                break
        return added

    def selected_count(candidates: list[dict[str, Any]]) -> int:
        return sum((1 for item in candidates if str(item.get('id') or '') in selected_ids))
    coverage_budget = min(10, limit)
    kind_budgets = {'file_inspected': min(4, limit), 'symbol': min(5, limit), 'dependency': min(5, limit), 'pass_observation': min(4, limit)}
    late_budget = min(4, limit)
    append_candidates(coverage_candidates, min(2, coverage_budget))
    append_candidates(structural_candidates, 1)
    append_candidates(late_candidates, min(1, late_budget))
    coverage_used = selected_count(coverage_candidates)
    kind_used = {kind: selected_count(candidates) for kind, candidates in by_kind.items()}
    late_used = selected_count(late_candidates)
    coverage_used += append_candidates(coverage_candidates, coverage_budget - coverage_used)
    for kind in ('symbol', 'dependency', 'pass_observation', 'file_inspected'):
        kind_used[kind] += append_candidates(by_kind[kind], kind_budgets[kind] - kind_used[kind])
    append_candidates(late_candidates, late_budget - late_used)
    append_candidates(observations, limit - len(selected))
    return [{'id': item.get('id'), 'pass': item.get('pass'), 'path': item.get('path'), 'kind': item.get('kind'), 'summary': item.get('summary')} for item in selected[:limit]]
