from __future__ import annotations

import json
from typing import Any, Callable
from Agency.Core.runtime.resourcefulness import (
    compact_resourcefulness_context,
    resourcefulness_compression_diagnostics,
    trim_resourcefulness_context_for_prompt,
)


class PlanningPromptBudgetError(ValueError):
    def __init__(self, message: str, diagnostics: dict[str, Any]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


def build_planning_prompt(context: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    shape = 'Keys: intent_summary, problem_definition, current_system_model, causal_findings, assumptions, unresolved_questions, scope, implementation_strategy, risks, verification_strategy, rollback_strategy, proposal_boundaries, inspection_assessment.'
    max_chars = 2800
    resourcefulness_source = context.get('resourcefulness_context', [])
    if not isinstance(resourcefulness_source, list):
        resourcefulness_source = []

    def build_compact(tier: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        resourcefulness = trim_resourcefulness_context_for_prompt(resourcefulness_source, max_paths_per_category=tier['resourcefulness_paths'], max_relationships=tier['relationships'], max_unresolved=tier['resourcefulness_unresolved'], max_signals_per_path=tier['signals'], max_observations_per_path=tier['path_observations'])
        compact: dict[str, Any] = {'mission_id': context.get('mission_id'), 'intent': str(context.get('intent') or '')[:tier['intent_chars']], 'coverage': context.get('coverage_summary', {}), 'status': context.get('inspection_status', {}), 'resourcefulness': resourcefulness, 'observations': context.get('high_value_observations', [])[:tier['observations']], 'files': context.get('inspected_file_inventory', [])[:tier['files']]}
        if tier['scopes']:
            compact['scopes'] = context.get('declared_scopes', [])[:6]
        if tier['next_files']:
            compact['next_files'] = context.get('next_files', [])[:tier['next_files']]
        if tier['unresolved']:
            compact['unresolved'] = context.get('coverage_unresolved', [])[:tier['unresolved']]
        if tier['notes']:
            compact['notes'] = str(context.get('operator_notes') or '')[:tier['notes']]
        return (compact, resourcefulness)

    def render_prompt(compact: dict[str, Any], *, compact_header: bool) -> str:
        if compact_header:
            return f"Return valid compact JSON only. No repo access. Cite observation_id in findings.\n{shape}\nContext:{json.dumps(compact, separators=(',', ':'))}\n"
        return f"Synthesize one compact architecture mission plan from persisted artifacts only.\nYou have no repository access. Use only supplied observation_id values as evidence.\nDistinguish fact from inference. Preserve unresolveds. Do not output patches or markdown.\nReturn valid JSON only. Keep arrays to 1-3 concise items.\n{shape}\n\nContext:\n{json.dumps(compact, separators=(',', ':'))}\n"

    def accept(prompt: str, resourcefulness: list[dict[str, Any]], tier_name: str) -> tuple[str, dict[str, Any]]:
        metadata: dict[str, Any] = {'planning_prompt_size': len(prompt)}
        if resourcefulness_source:
            diagnostics = resourcefulness_compression_diagnostics(resourcefulness_source, resourcefulness, final_prompt_size=len(prompt), configured_budget=max_chars)
            diagnostics['tier'] = tier_name
            metadata['resourcefulness_compression_diagnostics'] = diagnostics
        return (prompt, metadata)
    tiers = [{'name': 'normal', 'resourcefulness_paths': 2, 'relationships': 8, 'resourcefulness_unresolved': 6, 'signals': 4, 'path_observations': 3, 'observations': 12, 'files': 14, 'next_files': 6, 'unresolved': 4, 'notes': 280, 'scopes': True, 'intent_chars': 1200, 'compact_header': False}, {'name': 'reduced', 'resourcefulness_paths': 1, 'relationships': 4, 'resourcefulness_unresolved': 3, 'signals': 2, 'path_observations': 2, 'observations': 6, 'files': 6, 'next_files': 0, 'unresolved': 2, 'notes': 0, 'scopes': True, 'intent_chars': 700, 'compact_header': True}, {'name': 'minimal', 'resourcefulness_paths': 1, 'relationships': 0, 'resourcefulness_unresolved': 0, 'signals': 0, 'path_observations': 1, 'observations': 4, 'files': 2, 'next_files': 0, 'unresolved': 0, 'notes': 0, 'scopes': False, 'intent_chars': 360, 'compact_header': True}]
    last_prompt = ''
    last_resourcefulness: list[dict[str, Any]] = []
    for tier in tiers:
        (compact, resourcefulness) = build_compact(tier)
        prompt = render_prompt(compact, compact_header=bool(tier['compact_header']))
        last_prompt = prompt
        last_resourcefulness = resourcefulness
        if len(prompt) <= max_chars:
            return accept(prompt, resourcefulness, str(tier['name']))
    compact = {'mission_id': context.get('mission_id'), 'intent': str(context.get('intent') or '')[:180], 'resourcefulness': trim_resourcefulness_context_for_prompt(resourcefulness_source, max_paths_per_category=1, max_relationships=0, max_unresolved=0, max_signals_per_path=0, max_observations_per_path=0)}
    prompt = render_prompt(compact, compact_header=True)
    if len(prompt) <= max_chars:
        return accept(prompt, compact.get('resourcefulness', []), 'category_floor')
    diagnostics: dict[str, Any] = {}
    if resourcefulness_source:
        diagnostics = resourcefulness_compression_diagnostics(resourcefulness_source, last_resourcefulness, final_prompt_size=len(last_prompt), configured_budget=max_chars)
        diagnostics['tier'] = 'budget_exceeded'
    raise PlanningPromptBudgetError(f'planning prompt budget exceeded after category-preserving compression: {len(prompt)} > {max_chars}', diagnostics)
