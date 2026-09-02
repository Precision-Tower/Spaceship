from __future__ import annotations

from Agency.Core.runtime.commands import mission_command
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from Agency.Core.runtime.resourcefulness import trim_resourcefulness_context_for_prompt


@dataclass(frozen=True)
class ProposalGenerationDependencies:
    """Local infrastructure required by the proposal-generation engine."""

    MISSION_SCHEMA_VERSION: int
    PROPOSAL_MAX_NEW_TOKENS: int
    _append_mission_event: Callable[..., Any]
    _as_string_list: Callable[..., Any]
    _assess_plan_proposal_readiness: Callable[..., Any]
    _atomic_json: Callable[..., Any]
    _atomic_text: Callable[..., Any]
    _call_model: Callable[..., Any]
    _dedupe_manifest_paths: Callable[..., Any]
    _load_operator_notes: Callable[..., Any]
    _load_plan: Callable[..., Any]
    _load_required_mission_json: Callable[..., Any]
    _mission_intent_path: Callable[..., Path]
    _mission_plan_json_path: Callable[..., Path]
    _mission_proposal_dir: Callable[..., Path]
    _mission_proposal_json_path: Callable[..., Path]
    _mission_proposal_md_path: Callable[..., Path]
    _mission_state_path: Callable[..., Path]
    _next_action_after_plan: Callable[..., Any]
    _now: Callable[[], str]
    _parse_model_json_object: Callable[..., Any]
    _require_model_ready: Callable[..., Any]
    _resolve_mission_dir: Callable[[str | None], Path]
    _stable: Callable[[Path], str]
    refresh_pinboard: Callable[..., Any]
    emit: Callable[[dict[str, Any]], None]


def _load_proposal_inputs(deps: ProposalGenerationDependencies, mission_dir: Path) -> dict[str, Any]:
    return {'intent': deps._load_required_mission_json(deps._mission_intent_path(mission_dir)), 'state': deps._load_required_mission_json(deps._mission_state_path(mission_dir)), 'plan': deps._load_plan(mission_dir), 'operator_notes': deps._load_operator_notes(mission_dir)}

def _assess_proposal_readiness(deps: ProposalGenerationDependencies, inputs: dict[str, Any]) -> dict[str, Any]:
    state = inputs.get('state', {})
    plan = inputs.get('plan', {})
    mission_id = str(plan.get('mission_id') or state.get('mission_id') or '')
    if not isinstance(plan, dict) or not plan:
        return {'ready': False, 'error': 'plan_required', 'reason': 'plan/plan.json is required.'}
    if plan.get('authority') != 'planning_synthesis_only':
        return {'ready': False, 'error': 'invalid_plan', 'reason': 'Plan authority is not planning_synthesis_only.'}
    if not plan.get('causal_findings'):
        return {'ready': False, 'error': 'invalid_plan', 'reason': 'Plan contains no causal findings.'}
    if state.get('planning_complete') is False:
        return {'ready': False, 'error': 'plan_required', 'reason': 'Mission state does not mark planning complete.'}
    readiness = deps._assess_plan_proposal_readiness(plan)
    if not readiness.get('ready'):
        return {**readiness, 'next_action': deps._next_action_after_plan(mission_id, plan, state=state)}
    return readiness

def _proposal_system_context(deps: ProposalGenerationDependencies) -> str:
    return 'You convert an approved architecture plan into an implementation proposal.\nYou are not inspecting, redesigning, or writing code.\nUse only supplied mission artifacts.\nDo not invent repository information.\nDo not output patches or source code.\nReturn valid compact JSON only.'

def _build_mission_proposal_prompt(deps: ProposalGenerationDependencies, inputs: dict[str, Any]) -> str:
    plan = inputs.get('plan', {})
    strategy = plan.get('implementation_strategy', {})
    scope = plan.get('scope', {})
    boundaries = plan.get('proposal_boundaries', {})
    assessment = plan.get('inspection_assessment', {})
    compact = {'mission_id': plan.get('mission_id'), 'intent': plan.get('intent_summary'), 'problem': plan.get('problem_definition'), 'findings': [{'id': item.get('id'), 'claim': item.get('claim'), 'confidence': item.get('confidence')} for item in plan.get('causal_findings', [])[:5] if isinstance(item, dict)], 'system_model': plan.get('current_system_model', {}), 'resourcefulness': trim_resourcefulness_context_for_prompt(plan.get('resourcefulness', []) if isinstance(plan.get('resourcefulness', []), list) else [], max_categories=5, max_paths_per_category=1, max_relationships=4, max_unresolved=3), 'likely_files': scope.get('likely_modified_files', [])[:10] if isinstance(scope, dict) else [], 'files_requiring_confirmation': scope.get('files_requiring_confirmation', [])[:8] if isinstance(scope, dict) else [], 'strategy': {'summary': strategy.get('summary') if isinstance(strategy, dict) else '', 'stages': strategy.get('stages', [])[:4] if isinstance(strategy, dict) else []}, 'risks': plan.get('risks', [])[:5], 'verification': plan.get('verification_strategy', [])[:8], 'rollback': plan.get('rollback_strategy', [])[:6], 'boundaries': boundaries if isinstance(boundaries, dict) else {}, 'sufficient_for_proposal': assessment.get('sufficient_for_proposal') if isinstance(assessment, dict) else False, 'operator_notes': str(inputs.get('operator_notes') or '')[:240]}
    shape = 'Keys: summary, implementation_units, execution_order, shared_risks, proposal_assumptions, operator_decisions_required, expected_side_effects, acceptance_criteria. Each unit needs objective, expected_files, dependencies, changes[{kind,path,reason}], verification, rollback, supported_by finding ids.'
    prompt = f"Convert the approved architecture plan into an implementation proposal.\nDo not inspect, redesign, add scope, output code, or create patches.\nUse only the supplied plan data. Reference planning findings by id in supported_by.\nReturn compact valid JSON only. {shape}\nContext:{json.dumps(compact, separators=(',', ':'))}\n"
    max_chars = 3000
    if len(prompt) > max_chars:
        compact['system_model'] = {}
        compact['resourcefulness'] = trim_resourcefulness_context_for_prompt(plan.get('resourcefulness', []) if isinstance(plan.get('resourcefulness', []), list) else [], max_categories=3, max_paths_per_category=1, max_relationships=2, max_unresolved=2)
        compact['files_requiring_confirmation'] = compact['files_requiring_confirmation'][:4]
        compact['risks'] = compact['risks'][:3]
        compact['verification'] = compact['verification'][:4]
        compact['rollback'] = compact['rollback'][:3]
        compact['operator_notes'] = ''
        prompt = f"Convert approved plan to implementation proposal JSON only.\nNo inspection, redesign, code, patches, or new scope. Use supported_by finding ids.\n{shape}\nContext:{json.dumps(compact, separators=(',', ':'))}\n"
    return prompt

def _plan_finding_ids(deps: ProposalGenerationDependencies, plan: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in plan.get('causal_findings', []):
        if isinstance(item, dict):
            value = str(item.get('id') or '').strip()
            if value:
                ids.append(value)
    return ids

def _first_finding_ids(deps: ProposalGenerationDependencies, plan: dict[str, Any], *, limit: int=3) -> list[str]:
    ids = _plan_finding_ids(deps, plan)
    return ids[:limit] or ['finding-001']

def _normalize_change_item(deps: ProposalGenerationDependencies, raw: Any, default_path: str) -> dict[str, str] | None:
    if isinstance(raw, dict):
        kind = str(raw.get('kind') or 'modify').strip()
        path = str(raw.get('path') or default_path).strip()
        reason = str(raw.get('reason') or '').strip()
    else:
        kind = 'modify'
        path = default_path
        reason = str(raw or '').strip()
    if not path:
        return None
    if kind not in {'modify', 'add', 'create', 'remove', 'delete', 'rename', 'verify'}:
        kind = 'modify'
    return {'kind': kind, 'path': path, 'reason': reason or 'Required by the implementation unit objective.'}

def _normalize_supported_by(deps: ProposalGenerationDependencies, raw: Any, plan: dict[str, Any]) -> list[str]:
    valid = set(_plan_finding_ids(deps, plan))
    values: list[str] = []
    if isinstance(raw, list):
        candidates = raw
    else:
        candidates = []
    for item in candidates:
        value = str(item.get('id') if isinstance(item, dict) else item).strip()
        if value in valid and value not in values:
            values.append(value)
    return values or _first_finding_ids(deps, plan, limit=2)

def _normalize_proposal_acceptance_criteria(deps: ProposalGenerationDependencies, raw: Any) -> list[Any]:
    criteria: list[Any] = []
    if not isinstance(raw, list):
        return criteria
    for item in raw:
        if isinstance(item, dict):
            text = str(item.get('criterion') or item.get('description') or item.get('text') or item.get('name') or '').strip()
            if not text:
                continue
            normalized: dict[str, Any] = {'criterion': text}
            criterion_id = str(item.get('id') or item.get('criterion_id') or '').strip()
            if criterion_id:
                normalized['id'] = criterion_id
            evaluation = item.get('evaluation')
            if isinstance(evaluation, dict):
                normalized['evaluation'] = evaluation
            metadata = item.get('metadata')
            if isinstance(metadata, dict):
                normalized['metadata'] = metadata
            criteria.append(normalized)
        else:
            text = str(item).strip()
            if text:
                criteria.append(text)
        if len(criteria) >= 10:
            break
    return criteria

def _normalize_proposal_visual_checks(deps: ProposalGenerationDependencies, raw: Any) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return checks
    for item in raw:
        if not isinstance(item, dict):
            continue
        checks.append({'capture_id': str(item.get('capture_id') or item.get('id') or '').strip(), 'required': bool(item.get('required', True)), 'purpose': str(item.get('purpose') or '').strip(), 'criterion_id': str(item.get('criterion_id') or item.get('criterion') or '').strip(), 'backend': str(item.get('backend') or 'mock').strip(), 'output_name': str(item.get('output_name') or item.get('path') or '').strip(), 'target': item.get('target') if isinstance(item.get('target'), dict) else {}, 'timing': item.get('timing') if isinstance(item.get('timing'), dict) else {}, 'metadata': item.get('metadata') if isinstance(item.get('metadata'), dict) else {}})
        if len(checks) >= 12:
            break
    return checks

def _normalize_proposal_payload(deps: ProposalGenerationDependencies, model_proposal: dict[str, Any], inputs: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    plan = inputs.get('plan', {})
    scope = plan.get('scope', {})
    strategy = plan.get('implementation_strategy', {})
    stages = strategy.get('stages', []) if isinstance(strategy, dict) else []
    likely_files = deps._dedupe_manifest_paths(scope.get('likely_modified_files', [])) if isinstance(scope, dict) else []
    verification_defaults = deps._as_string_list(plan.get('verification_strategy'), limit=8)
    rollback_defaults = deps._as_string_list(plan.get('rollback_strategy'), limit=8)
    raw_units = model_proposal.get('implementation_units', [])
    units: list[dict[str, Any]] = []
    if isinstance(raw_units, list):
        for raw in raw_units:
            if not isinstance(raw, dict):
                continue
            expected_files = deps._dedupe_manifest_paths(raw.get('expected_files', [])) or likely_files[:6]
            changes: list[dict[str, str]] = []
            raw_changes = raw.get('changes', [])
            if isinstance(raw_changes, list):
                for change in raw_changes:
                    normalized = _normalize_change_item(deps, change, expected_files[0] if expected_files else '')
                    if normalized:
                        changes.append(normalized)
                    if len(changes) >= 8:
                        break
            if not changes:
                changes = [{'kind': 'modify', 'path': path, 'reason': 'Expected implementation surface from the architecture plan.'} for path in expected_files[:4]]
            units.append({'id': f'unit-{len(units) + 1:03d}', 'objective': str(raw.get('objective') or raw.get('name') or 'Implement a bounded plan stage.').strip(), 'expected_files': expected_files, 'dependencies': deps._as_string_list(raw.get('dependencies'), limit=8), 'changes': changes, 'verification': deps._as_string_list(raw.get('verification'), limit=8) or verification_defaults, 'rollback': deps._as_string_list(raw.get('rollback'), limit=8) or rollback_defaults, 'supported_by': _normalize_supported_by(deps, raw.get('supported_by', []), plan)})
            if len(units) >= 6:
                break
    if not units:
        for stage in stages[:4]:
            if not isinstance(stage, dict):
                continue
            expected_files = deps._dedupe_manifest_paths(stage.get('expected_files', [])) or likely_files[:6]
            units.append({'id': f'unit-{len(units) + 1:03d}', 'objective': str(stage.get('objective') or stage.get('name') or 'Implement bounded plan stage.').strip(), 'expected_files': expected_files, 'dependencies': deps._as_string_list(stage.get('dependencies'), limit=8), 'changes': [{'kind': 'modify', 'path': path, 'reason': 'Expected implementation file from architecture plan stage.'} for path in expected_files[:4]], 'verification': deps._as_string_list(stage.get('verification'), limit=8) or verification_defaults, 'rollback': rollback_defaults or ['Revert this unit as a standalone source change.'], 'supported_by': _first_finding_ids(deps, plan, limit=2)})
        if not units:
            expected_files = likely_files[:6]
            units.append({'id': 'unit-001', 'objective': 'Prepare a bounded implementation proposal from the approved architecture plan.', 'expected_files': expected_files, 'dependencies': [], 'changes': [{'kind': 'modify', 'path': path, 'reason': 'Likely modified file identified by the architecture plan.'} for path in expected_files[:4]], 'verification': verification_defaults or ['Run the verification checks named in the architecture plan.'], 'rollback': rollback_defaults or ['Revert this unit independently if verification fails.'], 'supported_by': _first_finding_ids(deps, plan, limit=2)})
    execution_order = deps._as_string_list(model_proposal.get('execution_order'), limit=12)
    unit_ids = [unit['id'] for unit in units]
    normalized_order: list[str] = []
    for item in execution_order:
        if item in unit_ids and item not in normalized_order:
            normalized_order.append(item)
            continue
        try:
            index = int(item) - 1
        except ValueError:
            index = -1
        if 0 <= index < len(unit_ids) and unit_ids[index] not in normalized_order:
            normalized_order.append(unit_ids[index])
    execution_order = normalized_order
    if not execution_order:
        execution_order = [unit['id'] for unit in units]
    acceptance_criteria = _normalize_proposal_acceptance_criteria(deps, model_proposal.get('acceptance_criteria')) or ['Implementation remains source-only until operator approval and verification succeeds.']
    return {'schema_version': deps.MISSION_SCHEMA_VERSION, 'mission_id': str(plan.get('mission_id') or inputs.get('intent', {}).get('mission_id') or ''), 'created_at': created_at, 'authority': 'implementation_proposal', 'summary': str(model_proposal.get('summary') or f"Implementation proposal for: {plan.get('intent_summary', '')}").strip(), 'implementation_units': units, 'execution_order': execution_order, 'shared_risks': deps._as_string_list(model_proposal.get('shared_risks'), limit=10) or [item.get('description') for item in plan.get('risks', [])[:5] if isinstance(item, dict) and item.get('description')], 'proposal_assumptions': deps._as_string_list(model_proposal.get('proposal_assumptions'), limit=10) or [item.get('statement') for item in plan.get('assumptions', [])[:5] if isinstance(item, dict) and item.get('statement')], 'operator_decisions_required': deps._as_string_list(model_proposal.get('operator_decisions_required'), limit=10) or [item.get('question') for item in plan.get('unresolved_questions', [])[:5] if isinstance(item, dict) and item.get('question')], 'expected_side_effects': deps._as_string_list(model_proposal.get('expected_side_effects'), limit=10), 'acceptance_criteria': acceptance_criteria, 'visual_checks': _normalize_proposal_visual_checks(deps, model_proposal.get('visual_checks')), 'implementation_not_started': True, 'plan_reference': {'path': 'plan/plan.json', 'created_at': plan.get('created_at'), 'findings': _plan_finding_ids(deps, plan)}}

def _validate_proposal(deps: ProposalGenerationDependencies, proposal: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ('schema_version', 'mission_id', 'authority', 'summary', 'implementation_units', 'execution_order', 'implementation_not_started'):
        if key not in proposal:
            errors.append(f'missing {key}')
    if proposal.get('authority') != 'implementation_proposal':
        errors.append('authority must be implementation_proposal')
    if proposal.get('implementation_not_started') is not True:
        errors.append('implementation_not_started must be true')
    valid_findings = set(_plan_finding_ids(deps, plan))
    if not valid_findings:
        errors.append('plan has no findings to support proposal')
    unit_ids: set[str] = set()
    for unit in proposal.get('implementation_units', []):
        if not isinstance(unit, dict):
            errors.append('implementation_units contains non-object item')
            continue
        unit_id = str(unit.get('id') or '')
        if not unit_id:
            errors.append('implementation unit missing id')
        unit_ids.add(unit_id)
        supported_by = unit.get('supported_by', [])
        if not supported_by:
            errors.append(f"{unit_id or 'unit'} has no supported_by findings")
        for finding_id in supported_by:
            if finding_id not in valid_findings:
                errors.append(f"{unit_id or 'unit'} references unknown finding {finding_id}")
        if not unit.get('changes'):
            errors.append(f"{unit_id or 'unit'} has no changes")
    for unit_id in proposal.get('execution_order', []):
        if unit_id not in unit_ids:
            errors.append(f'execution_order references unknown unit {unit_id}')
    return errors

def _render_proposal_markdown(deps: ProposalGenerationDependencies, proposal: dict[str, Any]) -> str:

    def bullet(items: list[Any]) -> list[str]:
        return [f'- {item}' for item in items] or ['- none']
    lines = ['# Mission Proposal', '', '## Summary', '', str(proposal.get('summary') or ''), '', '## Implementation Units']
    for unit in proposal.get('implementation_units', []):
        lines.extend(['', f"### {unit.get('id')}", '', str(unit.get('objective') or ''), '', 'Supported by:', *bullet(unit.get('supported_by', [])), '', 'Expected files:', *bullet(unit.get('expected_files', [])), '', 'Changes:'])
        for change in unit.get('changes', []):
            lines.append(f"- {change.get('kind')} {change.get('path')}: {change.get('reason')}")
        lines.extend(['', 'Verification:', *bullet(unit.get('verification', [])), '', 'Rollback:', *bullet(unit.get('rollback', []))])
    lines.extend(['', '## Execution Order', *bullet(proposal.get('execution_order', [])), '', '## Dependencies'])
    for unit in proposal.get('implementation_units', []):
        lines.append(f"- {unit.get('id')}: {', '.join(unit.get('dependencies', [])) or 'none'}")
    lines.extend(['', '## Operator Decisions', *bullet(proposal.get('operator_decisions_required', [])), '', '## Verification'])
    verification: list[str] = []
    for unit in proposal.get('implementation_units', []):
        verification.extend(unit.get('verification', []))
    lines.extend(bullet(deps._dedupe_manifest_paths(verification)))
    lines.extend(['', '## Rollback'])
    rollback: list[str] = []
    for unit in proposal.get('implementation_units', []):
        rollback.extend(unit.get('rollback', []))
    lines.extend(bullet(deps._dedupe_manifest_paths(rollback)))
    lines.extend(['', '## Acceptance Criteria', *bullet(proposal.get('acceptance_criteria', [])), '', '## Shared Risks', *bullet(proposal.get('shared_risks', [])), '', '## Proposal Assumptions', *bullet(proposal.get('proposal_assumptions', [])), '', f"Implementation not started: {proposal.get('implementation_not_started')}", ''])
    return '\n'.join(lines)

def _update_state_after_proposal(deps: ProposalGenerationDependencies, state_data: dict[str, Any], mission_id: str, proposal_path: Path, *, created_at: str) -> dict[str, Any]:
    unresolved: list[str] = []
    for item in state_data.get('unresolved', []):
        text = str(item)
        if text == 'No implementation proposal exists.':
            continue
        if text not in unresolved:
            unresolved.append(text)
    if 'Implementation has not started.' not in unresolved:
        unresolved.append('Implementation has not started.')
    return {**state_data, 'schema_version': state_data.get('schema_version', deps.MISSION_SCHEMA_VERSION), 'mission_id': mission_id, 'updated_at': created_at, 'phase': 'proposed', 'status': 'proposal_complete', 'planning_complete': True, 'proposals_complete': True, 'unresolved': unresolved, 'next_action': {'command': mission_command('implement', mission_id), 'authority': 'operator_approval_required', 'reason': 'Proposal awaits operator approval.'}, 'proposal': {'path': deps._stable(proposal_path), 'created_at': created_at, 'schema_version': deps.MISSION_SCHEMA_VERSION}}

def _proposal_failure(deps: ProposalGenerationDependencies, status: str, mission_id: str | None, reason: str, *, next_action: dict[str, Any] | None=None, extra: dict[str, Any] | None=None, exit_code: int=1) -> int:
    payload = {'ok': False, 'status': status, 'error': status, 'mission_id': mission_id, 'reason': reason, 'authority': 'implementation_proposal', 'source_files_modified': False}
    if next_action:
        payload['next_action'] = next_action
    if extra:
        payload.update(extra)
    deps.emit(payload)
    return exit_code

def run_mission_propose(deps: ProposalGenerationDependencies, mission: str | None) -> int:
    try:
        mission_dir = deps._resolve_mission_dir(mission)
    except ValueError as exc:
        return _proposal_failure(deps, 'mission_not_found', str(mission), str(exc), exit_code=2)
    mission_id = mission_dir.name
    proposal_json_path = deps._mission_proposal_json_path(mission_dir)
    proposal_md_path = deps._mission_proposal_md_path(mission_dir)
    if proposal_json_path.exists() or proposal_md_path.exists():
        payload = {'ok': False, 'status': 'proposal_already_exists', 'mission_id': mission_id, 'proposal_path': deps._stable(proposal_json_path), 'markdown_path': deps._stable(proposal_md_path), 'authority': 'implementation_proposal', 'source_files_modified': False}
        deps.emit(payload)
        return 0
    if not deps._mission_plan_json_path(mission_dir).exists():
        next_action = {'command': mission_command('plan', mission_id), 'authority': 'read_only_planning'}
        return _proposal_failure(deps, 'plan_required', mission_id, 'plan/plan.json is required before mission proposal generation.', next_action=next_action, exit_code=1)
    try:
        inputs = _load_proposal_inputs(deps, mission_dir)
    except ValueError as exc:
        return _proposal_failure(deps, 'invalid_plan', mission_id, str(exc), exit_code=2)
    readiness = _assess_proposal_readiness(deps, inputs)
    if not readiness.get('ready'):
        error = str(readiness.get('error') or 'invalid_plan')
        next_action = readiness.get('next_action') if isinstance(readiness.get('next_action'), dict) else None
        if error == 'plan_required' and next_action is None:
            next_action = {'command': mission_command('plan', mission_id), 'authority': 'read_only_planning'}
        return _proposal_failure(deps, error, mission_id, str(readiness.get('reason') or 'Plan is not ready for proposal generation.'), next_action=next_action, exit_code=1)
    ready, model_server_status, _started_model_server = deps._require_model_ready(start_model_server=False)
    if not ready:
        return _proposal_failure(deps, 'model_inference_failed', mission_id, 'Model server is not ready for mission proposal generation.', extra={'model_server_status': model_server_status}, exit_code=1)
    prompt = _build_mission_proposal_prompt(deps, inputs)
    model_response = deps._call_model(prompt, _proposal_system_context(deps), deps.PROPOSAL_MAX_NEW_TOKENS)
    draft = str(model_response.get('draft') or '').strip()
    if not model_response.get('ok') or model_response.get('status') != 'draft_generated' or (not draft):
        return _proposal_failure(deps, 'model_inference_failed', mission_id, 'Proposal model did not return a usable draft.', extra={'model_response': model_response, 'model_server_status': model_server_status}, exit_code=1)
    parsed_model_proposal = deps._parse_model_json_object(draft)
    if parsed_model_proposal is None:
        return _proposal_failure(deps, 'invalid_proposal_response', mission_id, 'Proposal model response was not valid JSON.', extra={'model_response_status': model_response.get('status'), 'model_draft_excerpt': draft[:1200]}, exit_code=1)
    created_at = deps._now()
    proposal_payload = _normalize_proposal_payload(deps, parsed_model_proposal, inputs, created_at=created_at)
    validation_errors = _validate_proposal(deps, proposal_payload, inputs['plan'])
    if validation_errors:
        return _proposal_failure(deps, 'invalid_proposal_response', mission_id, 'Normalized proposal failed validation.', extra={'validation_errors': validation_errors}, exit_code=1)
    try:
        deps._mission_proposal_dir(mission_dir).mkdir(parents=True, exist_ok=True)
        deps._atomic_json(proposal_json_path, proposal_payload)
        deps._atomic_text(proposal_md_path, _render_proposal_markdown(deps, proposal_payload))
        state_payload = _update_state_after_proposal(deps, inputs['state'], mission_id, proposal_json_path, created_at=created_at)
        deps._atomic_json(deps._mission_state_path(mission_dir), state_payload)
    except Exception as exc:
        return _proposal_failure(deps, 'proposal_write_failed', mission_id, f'{type(exc).__name__}: {exc}', exit_code=1)
    observation = {'command': 'mission propose', 'status': 'proposal_complete', 'mission_id': mission_id, 'proposal_path': deps._stable(proposal_json_path), 'markdown_path': deps._stable(proposal_md_path), 'source_files_modified': False, 'authority': 'implementation_proposal'}
    deps._append_mission_event(mission_dir, 'proposed', observation)
    deps.refresh_pinboard(mission=str(inputs['intent'].get('intent') or mission_id), last_observation=observation, next_action=state_payload['next_action'])
    payload = {'ok': True, 'status': 'proposal_complete', 'mission_id': mission_id, 'proposal_path': deps._stable(proposal_json_path), 'markdown_path': deps._stable(proposal_md_path), 'implementation_units': len(proposal_payload.get('implementation_units', [])), 'next_action': state_payload['next_action'], 'source_files_modified': False, 'authority': 'implementation_proposal'}
    deps.emit(payload)
    return 0