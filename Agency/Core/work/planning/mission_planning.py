from __future__ import annotations

from Agency.Core.runtime.commands import mission_command
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from Agency.Core.runtime.resourcefulness import (
    compact_resourcefulness_context,
    resourcefulness_compression_diagnostics,
    trim_resourcefulness_context_for_prompt,
)

from Agency.Core.knowledge.reasoning import (
    first_evidence_ref,
    normalize_evidence_refs,
    build_reasoning_context,
)

from Agency.Core.work.planning.prompting import (
    PlanningPromptBudgetError,
    build_planning_prompt,
)


@dataclass(frozen=True)
class MissionPlanningDependencies:
    """Local infrastructure required by the plan/replan engine."""

    INSPECTION_CLASSES: tuple[str, ...]
    MISSION_COVERAGE_CATEGORIES: tuple[str, ...]
    MISSION_SCHEMA_VERSION: int
    PLAN_MAX_NEW_TOKENS: int
    _append_mission_event: Callable[..., Any]
    _as_string_list: Callable[..., Any]
    _assess_plan_proposal_readiness: Callable[..., Any]
    _atomic_json: Callable[..., Any]
    _atomic_text: Callable[..., Any]
    _call_model: Callable[..., Any]
    _dedupe_manifest_paths: Callable[..., Any]
    _load_json: Callable[..., Any]
    _load_operator_notes: Callable[..., Any]
    _load_required_mission_json: Callable[..., Any]
    _mission_coverage_path: Callable[..., Path]
    _mission_inspect_dir: Callable[..., Path]
    _mission_intent_path: Callable[..., Path]
    _mission_manifest_path: Callable[..., Path]
    _mission_plan_dir: Callable[..., Path]
    _mission_plan_json_path: Callable[..., Path]
    _mission_proposal_json_path: Callable[..., Path]
    _mission_proposal_md_path: Callable[..., Path]
    _mission_state_path: Callable[..., Path]
    _next_action_after_plan: Callable[..., Any]
    _scope_expansion_candidates: Callable[..., Any]
    _now: Callable[[], str]
    _parse_model_json_object: Callable[..., Any]
    _require_model_ready: Callable[..., Any]
    _resolve_mission_dir: Callable[[str | None], Path]
    _stable: Callable[[Path], str]
    refresh_pinboard: Callable[..., Any]
    emit: Callable[[dict[str, Any]], None]


def _mission_plan_md_path(deps: MissionPlanningDependencies, mission_dir: Path) -> Path:
    return deps._mission_plan_dir(mission_dir) / 'plan.md'

def _load_inspection_passes(deps: MissionPlanningDependencies, mission_dir: Path) -> list[dict[str, Any]]:
    passes: list[dict[str, Any]] = []
    for path in sorted(deps._mission_inspect_dir(mission_dir).glob('pass_*.json')):
        data = deps._load_json(path)
        if data is None or 'load_error' in data:
            raise ValueError(f'invalid inspection pass artifact: {deps._stable(path)}')
        try:
            pass_number = int(data.get('pass', path.stem.removeprefix('pass_')))
        except Exception:
            pass_number = len(passes) + 1
        data['_pass_path'] = deps._stable(path)
        data['_pass_number'] = pass_number
        passes.append(data)
    return sorted(passes, key=lambda item: int(item.get('_pass_number', 0)))

def _load_optional_knowledge_artifacts(deps: MissionPlanningDependencies, mission_dir: Path) -> list[dict[str, Any]]:
    knowledge_dir = deps._mission_inspect_dir(mission_dir) / 'knowledge'
    if not knowledge_dir.exists():
        return []
    artifacts: list[dict[str, Any]] = []
    for path in sorted(knowledge_dir.glob('*.json')):
        data = deps._load_json(path)
        if data is None or 'load_error' in data:
            continue
        artifacts.append({'path': deps._stable(path), 'data': data})
    return artifacts

def _load_mission_artifacts(deps: MissionPlanningDependencies, mission_dir: Path) -> dict[str, Any]:
    return {'intent': deps._load_required_mission_json(deps._mission_intent_path(mission_dir)), 'state': deps._load_required_mission_json(deps._mission_state_path(mission_dir)), 'manifest': deps._load_required_mission_json(deps._mission_manifest_path(mission_dir)), 'coverage': deps._load_required_mission_json(deps._mission_coverage_path(mission_dir)), 'passes': _load_inspection_passes(deps, mission_dir), 'knowledge': _load_optional_knowledge_artifacts(deps, mission_dir), 'operator_notes': deps._load_operator_notes(mission_dir)}

def _normalize_inspection_evidence(deps: MissionPlanningDependencies, artifacts: dict[str, Any]) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    files_inspected: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    symbol_count = 0
    dependency_count = 0
    file_inventory_seen: set[tuple[int, str]] = set()

    for pass_data in artifacts.get('passes', []):
        pass_number = int(pass_data.get('_pass_number', pass_data.get('pass', 0)))
        file_classification = pass_data.get('file_classification', {})
        if not isinstance(file_classification, dict):
            file_classification = {}
        index = 1

        for item in pass_data.get('observations', []):
            if not item:
                continue
            observation_id = f'obs-{pass_number:03d}-{index:02d}'
            if isinstance(item, dict):
                kind = str(item.get('kind') or 'pass_observation').strip() or 'pass_observation'
                path = str(item.get('path') or '').strip()
                observation = dict(item)
                observation['id'] = observation_id
                observation['pass'] = pass_number
                observation['kind'] = kind
                observation['path'] = path or None
                if kind == 'file_inspected':
                    classification = str(item.get('class') or file_classification.get(path) or 'unclassified')
                    observation['class'] = classification
                    if not str(observation.get('summary') or '').strip():
                        observation['summary'] = f"Inspection pass {pass_number} read {classification} file {path} ({item.get('lines', '?')} lines)."
                    if path:
                        key = (pass_number, path)
                        if key not in file_inventory_seen:
                            file_inventory_seen.add(key)
                            files_inspected.append({'path': path, 'class': classification, 'pass': pass_number, 'observation_id': observation_id})
                else:
                    summary = str(item.get('summary') or '').strip()
                    observation['summary'] = summary or str(item)
                observations.append(observation)
            else:
                observations.append({'id': observation_id, 'pass': pass_number, 'path': None, 'kind': 'pass_observation', 'summary': str(item)})
            index += 1

        for file_item in pass_data.get('files_inspected', []):
            if not isinstance(file_item, dict):
                continue
            path = str(file_item.get('path') or '')
            if not path:
                continue
            classification = str(file_item.get('class') or file_classification.get(path) or 'unclassified')
            if (pass_number, path) in file_inventory_seen:
                continue
            observation = {'id': f'obs-{pass_number:03d}-{index:02d}', 'pass': pass_number, 'path': path, 'kind': 'file_inspected', 'summary': f"Inspection pass {pass_number} read {classification} file {path} ({file_item.get('lines', '?')} lines).", 'class': classification}
            observations.append(observation)
            file_inventory_seen.add((pass_number, path))
            files_inspected.append({'path': path, 'class': classification, 'pass': pass_number, 'observation_id': observation['id']})
            index += 1

        for symbol in pass_data.get('symbols', []):
            if not isinstance(symbol, dict):
                continue
            path = str(symbol.get('file') or '')
            name = str(symbol.get('name') or '')
            kind = str(symbol.get('kind') or 'symbol')
            if not path or not name or kind == 'truncated':
                continue
            observations.append({'id': f'obs-{pass_number:03d}-{index:02d}', 'pass': pass_number, 'path': path, 'kind': 'symbol', 'name': name, 'symbol_kind': kind, 'summary': f'{kind} {name} was recorded in {path}.'})
            symbol_count += 1
            index += 1
            if symbol_count >= 80:
                break

        for dependency in pass_data.get('dependencies', []):
            if not isinstance(dependency, dict):
                continue
            path = str(dependency.get('file') or '')
            target = str(dependency.get('target') or '')
            if not path or not target or dependency.get('kind') == 'truncated':
                continue
            observations.append({'id': f'obs-{pass_number:03d}-{index:02d}', 'pass': pass_number, 'path': path, 'kind': 'dependency', 'target': target, 'summary': f'{path} references {target}.'})
            dependency_count += 1
            index += 1
            if dependency_count >= 80:
                break

        for item in pass_data.get('unresolved', []):
            if not item:
                continue
            unresolved.append({'pass': pass_number, 'question': str(item), 'recommended_action': 'additional_inspection'})

    manifest = artifacts.get('manifest', {})
    coverage = artifacts.get('coverage', {})
    files_by_class = manifest.get('files_by_class', {})
    if not isinstance(files_by_class, dict):
        files_by_class = {}
    normalized_files_by_class = {
        class_name: deps._dedupe_manifest_paths(files_by_class.get(class_name, []))
        for class_name in deps.INSPECTION_CLASSES
    }
    return {'observations': observations, 'observations_by_id': {item['id']: item for item in observations}, 'files_inspected': files_inspected, 'files_by_class': normalized_files_by_class, 'files_remaining': deps._dedupe_manifest_paths(manifest.get('files_remaining', [])), 'coverage_summary': coverage.get('categories', {}), 'coverage_evidence': coverage.get('evidence', {}) if isinstance(coverage.get('evidence', {}), dict) else {}, 'coverage_unresolved': list(coverage.get('unresolved', [])) if isinstance(coverage.get('unresolved', []), list) else [], 'pass_unresolved': unresolved}

def _assess_planning_readiness(deps: MissionPlanningDependencies, artifacts: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    passes = artifacts.get('passes', [])
    manifest = artifacts.get('manifest', {})
    coverage = artifacts.get('coverage', {})
    files_discovered = deps._dedupe_manifest_paths(manifest.get('files_discovered', []))
    files_by_class = evidence.get('files_by_class', {})
    if not files_discovered and isinstance(files_by_class, dict):
        discovered_from_classes: list[Any] = []
        for class_name in deps.INSPECTION_CLASSES:
            values = files_by_class.get(class_name, [])
            if isinstance(values, list):
                discovered_from_classes.extend(values)
        files_discovered = deps._dedupe_manifest_paths(discovered_from_classes)
    observations = evidence.get('observations', [])
    file_observations = [item for item in observations if item.get('kind') == 'file_inspected']
    if not passes:
        return {'ready': False, 'reason': 'No inspection passes exist.', 'confidence': 'low', 'warnings': ['Run mission inspect before planning.']}
    if not observations or not file_observations:
        return {'ready': False, 'reason': 'No inspection passes contain usable observations.', 'confidence': 'low', 'warnings': ['Inspection artifacts do not contain file observations.']}
    if not files_discovered:
        return {'ready': False, 'reason': 'Inspection manifest does not represent the mission scope.', 'confidence': 'low', 'warnings': ['Mission scope is not represented in the inspection manifest.']}
    primary_seen = any((item.get('class') == 'primary' for item in file_observations))
    if not primary_seen and isinstance(files_by_class, dict):
        primary_paths = set(deps._dedupe_manifest_paths(files_by_class.get('primary', [])))
        inspected_paths = {
            str(item.get('path') or '')
            for item in file_observations
            if str(item.get('path') or '')
        }
        primary_seen = bool(primary_paths.intersection(inspected_paths))
    if not primary_seen:
        return {'ready': False, 'reason': 'No primary engineering source has been inspected yet.', 'confidence': 'low', 'warnings': ['Inspect at least one primary engineering source before planning.']}

    warnings: list[str] = []
    confidence = 'high'
    if not bool(coverage.get('inspection_complete', False)):
        remaining_files = evidence.get('files_remaining', [])
        remaining_count = len(remaining_files) if isinstance(remaining_files, list) else 0
        confidence = 'low'
        warnings.append(f'Inspection is incomplete: {remaining_count} discovered files remain uninspected.')
    coverage_summary = coverage.get('categories', {})
    if isinstance(coverage_summary, dict):
        partial_categories = [
            str(category) for category, status in coverage_summary.items()
            if str(status) in {'partial', 'not_started'}
        ]
        if partial_categories and confidence == 'high':
            confidence = 'medium'
        if partial_categories:
            suffix = '.' if len(partial_categories) <= 6 else ', ...'
            warnings.append('Coverage is partial for: ' + ', '.join(partial_categories[:6]) + suffix)
    return {'ready': True, 'reason': 'Inspection evidence is sufficient for bounded planning.', 'confidence': confidence, 'warnings': warnings}

def _planning_system_context(deps: MissionPlanningDependencies) -> str:
    return 'You are a mission planning synthesizer.\nYou do not have repository access.\nYou may only reason from supplied mission artifacts.\nDistinguish fact from inference.\nDo not claim to have inspected files absent from evidence.\nDo not fill gaps with confident guesses.\nDo not produce source diffs, patches, or implementation proposals.\nReturn only valid compact JSON.'

def _build_planning_context(
    artifacts: dict[str, Any],
    evidence: dict[str, Any],
    readiness: dict[str, Any],
    *,
    inspection_classes: tuple[str, ...] | list[str],
    coverage_categories: tuple[str, ...] | list[str],
    next_files: list[str],
    resourcefulness_context: list[dict[str, Any]],
) -> dict[str, Any]:
    intent = artifacts.get("intent", {})
    notes = str(artifacts.get("operator_notes") or "")

    reasoning_context = build_reasoning_context(
        artifacts,
        evidence,
        readiness,
        inspection_classes=inspection_classes,
        coverage_categories=coverage_categories,
        resourcefulness_context=resourcefulness_context,
    )

    # Preserve the planner context schema and field order.
    return {
        "mission_id": intent.get("mission_id"),
        "intent": intent.get("intent"),
        "declared_scopes": [
            item.get("relative", item)
            for item in intent.get("scopes", [])
        ],
        "coverage_summary": reasoning_context["coverage_summary"],
        "coverage_unresolved": reasoning_context["coverage_unresolved"],
        "inspection_status": reasoning_context["inspection_status"],
        "files_by_class_counts": reasoning_context["files_by_class_counts"],
        "high_value_observations": reasoning_context[
            "high_value_observations"
        ],
        "inspected_file_inventory": reasoning_context[
            "inspected_file_inventory"
        ],
        "next_files": next_files[:12],
        "operator_notes": notes[:1200],
        "knowledge_artifacts": [
            item.get("path")
            for item in artifacts.get("knowledge", [])
        ],
        "resourcefulness_context": reasoning_context[
            "resourcefulness_context"
        ],
    }




def _normalize_plan_payload(deps: MissionPlanningDependencies, model_plan: dict[str, Any], artifacts: dict[str, Any], evidence: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    intent = artifacts.get('intent', {})
    manifest = artifacts.get('manifest', {})
    coverage = artifacts.get('coverage', {})
    mission_id = str(intent.get('mission_id') or '')
    intent_text = str(intent.get('intent') or '')
    inspected_paths = [item['path'] for item in evidence.get('files_inspected', []) if item.get('path')]
    scope_input = model_plan.get('scope', {})
    if not isinstance(scope_input, dict):
        scope_input = {}
    likely_files = deps._dedupe_manifest_paths(scope_input.get('likely_modified_files', []))
    if not likely_files:
        likely_files = inspected_paths[:8]
    scope_expansion_candidates = deps._dedupe_manifest_paths(
        deps._scope_expansion_candidates(artifacts, evidence, model_plan)
    )
    files_requiring_confirmation = deps._dedupe_manifest_paths(scope_input.get('files_requiring_confirmation', []))
    if not files_requiring_confirmation:
        files_requiring_confirmation = scope_expansion_candidates or evidence.get('files_remaining', [])[:12]
    current_model = model_plan.get('current_system_model', {})
    if not isinstance(current_model, dict):
        current_model = {}
    system_model = {'components': deps._as_string_list(current_model.get('components')) or [f'Inspected artifact: {path}' for path in inspected_paths[:8]], 'control_flow': deps._as_string_list(current_model.get('control_flow')) or ['Control flow remains partially inferred from inspected scene/script dependencies.'], 'state_ownership': deps._as_string_list(current_model.get('state_ownership')) or ['State ownership needs confirmation during proposal scoping.'], 'integration_points': deps._as_string_list(current_model.get('integration_points')) or likely_files[:6]}
    findings: list[dict[str, Any]] = []
    raw_findings = model_plan.get('causal_findings', [])
    if isinstance(raw_findings, list):
        for raw in raw_findings:
            if not isinstance(raw, dict):
                continue
            refs = normalize_evidence_refs(
                raw.get('evidence', []),
                evidence,
            )
            claim = str(raw.get('claim') or '').strip()
            if not claim or not refs:
                continue
            confidence = str(raw.get('confidence') or 'medium').lower()
            if confidence not in {'low', 'medium', 'high'}:
                confidence = 'medium'
            findings.append({'id': f'finding-{len(findings) + 1:03d}', 'claim': claim, 'evidence': [ref.to_dict() for ref in refs], 'confidence': confidence})
    if not findings:
        first_ref = first_evidence_ref(evidence)
        if first_ref:
            findings.append({'id': 'finding-001', 'claim': 'The mission has persisted inspection evidence for primary engineering artifacts, but the plan should preserve partial knowledge until unresolved inspection gaps are addressed.', 'evidence': [first_ref.to_dict()], 'confidence': 'high'})

    def normalize_assumptions(value: Any) -> list[dict[str, str]]:
        assumptions: list[dict[str, str]] = []
        if isinstance(value, list):
            for raw in value:
                if isinstance(raw, dict):
                    statement = str(raw.get('statement') or '').strip()
                    reason = str(raw.get('reason') or '').strip()
                    risk = str(raw.get('risk_if_false') or '').strip()
                else:
                    statement = str(raw).strip()
                    reason = 'Model inference from partial inspection evidence.'
                    risk = 'The implementation proposal may target the wrong integration point.'
                if not statement:
                    continue
                assumptions.append({'id': f'assumption-{len(assumptions) + 1:03d}', 'statement': statement, 'reason': reason or 'Not directly proven by current inspection evidence.', 'risk_if_false': risk or 'The plan may need additional inspection before proposal generation.'})
                if len(assumptions) >= 8:
                    break
        if not assumptions:
            assumptions.append({'id': 'assumption-001', 'statement': 'The inspected artifacts are representative enough to support bounded planning.', 'reason': 'Planning readiness was based on persisted inspection evidence, not full repository completion.', 'risk_if_false': 'Additional inspection may change proposal boundaries.'})
        return assumptions

    def normalize_unresolved(value: Any) -> list[dict[str, Any]]:
        unresolved: list[dict[str, Any]] = []
        if isinstance(value, list):
            for raw in value:
                if isinstance(raw, dict):
                    question = str(raw.get('question') or '').strip()
                    blocking = bool(raw.get('blocking', True))
                    action = str(raw.get('recommended_action') or 'additional_inspection')
                else:
                    question = str(raw).strip()
                    blocking = True
                    action = 'additional_inspection'
                if not question:
                    continue
                unresolved.append({'id': f'unresolved-{len(unresolved) + 1:03d}', 'question': question, 'blocking': blocking, 'recommended_action': action})
                if len(unresolved) >= 10:
                    break
        for item in evidence.get('coverage_unresolved', [])[:6]:
            question = str(item).strip()
            if question and (not any((entry['question'] == question for entry in unresolved))):
                unresolved.append({'id': f'unresolved-{len(unresolved) + 1:03d}', 'question': question, 'blocking': False, 'recommended_action': 'additional_inspection'})
        return unresolved
    strategy_input = model_plan.get('implementation_strategy', {})
    if not isinstance(strategy_input, dict):
        strategy_input = {}
    stages: list[dict[str, Any]] = []
    raw_stages = strategy_input.get('stages', [])
    if isinstance(raw_stages, list):
        for raw in raw_stages:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get('name') or '').strip()
            objective = str(raw.get('objective') or '').strip()
            if not name and (not objective):
                continue
            stages.append({'order': len(stages) + 1, 'name': name or f'Stage {len(stages) + 1}', 'objective': objective or 'Advance the implementation strategy within inspected evidence boundaries.', 'dependencies': deps._as_string_list(raw.get('dependencies'), limit=8), 'expected_files': deps._dedupe_manifest_paths(raw.get('expected_files', []))[:10], 'verification': deps._as_string_list(raw.get('verification'), limit=8)})
            if len(stages) >= 6:
                break
    if not stages:
        stages.append({'order': 1, 'name': 'Bounded proposal preparation', 'objective': 'Prepare implementation proposals only for files supported by inspection evidence.', 'dependencies': [], 'expected_files': likely_files[:8], 'verification': ['Run the relevant audit and runtime checks named by inspected evidence.']})
    raw_risks = model_plan.get('risks', [])
    risks: list[dict[str, str]] = []
    if isinstance(raw_risks, list):
        for raw in raw_risks:
            if isinstance(raw, dict):
                description = str(raw.get('description') or '').strip()
                likelihood = str(raw.get('likelihood') or 'medium').lower()
                impact = str(raw.get('impact') or 'medium').lower()
                mitigation = str(raw.get('mitigation') or '').strip()
            else:
                description = str(raw).strip()
                likelihood = 'medium'
                impact = 'medium'
                mitigation = 'Use additional inspection before implementation.'
            if not description:
                continue
            if likelihood not in {'low', 'medium', 'high'}:
                likelihood = 'medium'
            if impact not in {'low', 'medium', 'high'}:
                impact = 'medium'
            risks.append({'id': f'risk-{len(risks) + 1:03d}', 'description': description, 'likelihood': likelihood, 'impact': impact, 'mitigation': mitigation or 'Keep proposal boundaries narrow and evidence-backed.'})
            if len(risks) >= 8:
                break
    if not risks:
        risks.append({'id': 'risk-001', 'description': 'Partial inspection may omit a required integration dependency.', 'likelihood': 'medium', 'impact': 'medium', 'mitigation': 'Use the remaining inspection queue before high-risk proposal generation.'})
    boundaries = model_plan.get('proposal_boundaries', {})
    if not isinstance(boundaries, dict):
        boundaries = {}
    assessment = model_plan.get('inspection_assessment', {})
    if not isinstance(assessment, dict):
        assessment = {}
    inspection_complete = bool(coverage.get('inspection_complete', False))
    coverage_summary = coverage.get('categories', {})
    if not isinstance(coverage_summary, dict):
        coverage_summary = {}
    unresolved_questions = normalize_unresolved(model_plan.get('unresolved_questions', []))
    sufficient_for_proposal = bool(assessment.get('sufficient_for_proposal', False))
    planning_confidence = str(assessment.get('planning_confidence') or '').lower()
    if planning_confidence not in {'low', 'medium', 'high'}:
        if not inspection_complete:
            planning_confidence = 'low'
        elif any(str(status) in {'partial', 'not_started'} for status in coverage_summary.values()):
            planning_confidence = 'medium'
        else:
            planning_confidence = 'high'
    warnings = deps._as_string_list(assessment.get('warnings'), limit=12)
    if not warnings and planning_confidence in {'low', 'medium'}:
        warnings = ['Plan confidence is limited by partial inspection coverage.']
    additional_inspection = deps._as_string_list(assessment.get('additional_inspection_recommended'), limit=12) or scope_expansion_candidates or evidence.get('files_remaining', [])[:12]
    return {'schema_version': deps.MISSION_SCHEMA_VERSION, 'mission_id': mission_id, 'created_at': created_at, 'authority': 'planning_synthesis_only', 'intent_summary': str(model_plan.get('intent_summary') or intent_text).strip(), 'problem_definition': str(model_plan.get('problem_definition') or 'Synthesize an architecture plan from persisted repository inspection evidence.').strip(), 'current_system_model': system_model, 'causal_findings': findings, 'assumptions': normalize_assumptions(model_plan.get('assumptions', [])), 'unresolved_questions': unresolved_questions, 'scope': {'in_scope': deps._as_string_list(scope_input.get('in_scope')) or [str(item.get('relative') or item.get('input') or item) for item in intent.get('scopes', [])], 'out_of_scope': deps._as_string_list(scope_input.get('out_of_scope')) or ['Source mutation during mission planning.', 'Implementation proposal generation.'], 'likely_modified_files': likely_files, 'files_requiring_confirmation': files_requiring_confirmation}, 'implementation_strategy': {'summary': str(strategy_input.get('summary') or 'Proceed in small proposals bounded by inspected evidence.').strip(), 'stages': stages}, 'risks': risks, 'verification_strategy': deps._as_string_list(model_plan.get('verification_strategy'), limit=12) or ['Use existing audit and runtime checks before accepting implementation.'], 'rollback_strategy': deps._as_string_list(model_plan.get('rollback_strategy'), limit=12) or ['Keep implementation proposals small enough to revert independently.'], 'proposal_boundaries': {'recommended_proposals': deps._as_string_list(boundaries.get('recommended_proposals'), limit=8) or ['Generate a narrow proposal for the highest-confidence integration path.'], 'do_not_combine': deps._as_string_list(boundaries.get('do_not_combine'), limit=8) or ['Do not combine implementation with verification artifact rewrites.']}, 'resourcefulness': compact_resourcefulness_context(artifacts), 'inspection_assessment': {'sufficient_for_planning': inspection_complete, 'sufficient_for_proposal': sufficient_for_proposal, 'planning_confidence': planning_confidence, 'warnings': warnings, 'coverage_summary': coverage_summary, 'additional_inspection_recommended': additional_inspection}}

def _validate_plan_payload(deps: MissionPlanningDependencies, plan: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ['schema_version', 'mission_id', 'created_at', 'problem_definition', 'current_system_model', 'causal_findings', 'assumptions', 'unresolved_questions', 'scope', 'implementation_strategy', 'risks', 'verification_strategy', 'rollback_strategy', 'proposal_boundaries', 'inspection_assessment']
    for key in required:
        if key not in plan:
            errors.append(f'missing {key}')
    observations = evidence.get('observations_by_id', {})
    for finding in plan.get('causal_findings', []):
        if not isinstance(finding, dict):
            errors.append('causal_findings contains non-object item')
            continue
        refs = finding.get('evidence', [])
        if not refs:
            errors.append(f"{finding.get('id', 'finding')} has no evidence")
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append(f"{finding.get('id', 'finding')} has invalid evidence reference")
                continue
            observation_id = str(ref.get('observation_id') or '')
            if observation_id not in observations:
                errors.append(f"{finding.get('id', 'finding')} cites unknown observation {observation_id}")
    return errors

def _render_plan_markdown(deps: MissionPlanningDependencies, plan: dict[str, Any]) -> str:

    def lines_for(items: list[Any], formatter) -> list[str]:
        lines: list[str] = []
        for item in items:
            lines.append(formatter(item))
        return lines or ['- none']
    model = plan.get('current_system_model', {})
    scope = plan.get('scope', {})
    strategy = plan.get('implementation_strategy', {})
    boundaries = plan.get('proposal_boundaries', {})
    assessment = plan.get('inspection_assessment', {})
    resourcefulness = plan.get('resourcefulness', [])
    lines = ['# Mission Plan', '', '## Intent', '', str(plan.get('intent_summary') or ''), '', '## Problem Definition', '', str(plan.get('problem_definition') or ''), '', '## Current System Model', '', '### Components', *lines_for(model.get('components', []), lambda item: f'- {item}'), '', '### Control Flow', *lines_for(model.get('control_flow', []), lambda item: f'- {item}'), '', '### State Ownership', *lines_for(model.get('state_ownership', []), lambda item: f'- {item}'), '', '### Integration Points', *lines_for(model.get('integration_points', []), lambda item: f'- {item}'), '', '## Evidence-Backed Findings']
    for finding in plan.get('causal_findings', []):
        evidence_refs = ', '.join((f"{ref.get('observation_id')} ({ref.get('path')})" for ref in finding.get('evidence', [])))
        lines.append(f"- {finding.get('id')}: {finding.get('claim')} [confidence: {finding.get('confidence')}; evidence: {evidence_refs}]")
    if not plan.get('causal_findings'):
        lines.append('- none')
    lines.extend(['', '## Assumptions', *lines_for(plan.get('assumptions', []), lambda item: f"- {item.get('id')}: {item.get('statement')} (reason: {item.get('reason')}; risk: {item.get('risk_if_false')})"), '', '## Unresolved Questions', *lines_for(plan.get('unresolved_questions', []), lambda item: f"- {item.get('id')}: {item.get('question')} (blocking: {item.get('blocking')}; action: {item.get('recommended_action')})"), '', '## Scope', '', '### In Scope', *lines_for(scope.get('in_scope', []), lambda item: f'- {item}'), '', '### Out Of Scope', *lines_for(scope.get('out_of_scope', []), lambda item: f'- {item}'), '', '### Likely Modified Files', *lines_for(scope.get('likely_modified_files', []), lambda item: f'- {item}'), '', '### Files Requiring Confirmation', *lines_for(scope.get('files_requiring_confirmation', []), lambda item: f'- {item}'), '', '## Implementation Strategy', '', str(strategy.get('summary') or '')])
    for stage in strategy.get('stages', []):
        lines.extend(['', f"### {stage.get('order')}. {stage.get('name')}", '', str(stage.get('objective') or ''), '', 'Expected files:', *lines_for(stage.get('expected_files', []), lambda item: f'- {item}'), '', 'Verification:', *lines_for(stage.get('verification', []), lambda item: f'- {item}')])
    lines.extend(['', '## Risks', *lines_for(plan.get('risks', []), lambda item: f"- {item.get('id')}: {item.get('description')} (likelihood: {item.get('likelihood')}; impact: {item.get('impact')}; mitigation: {item.get('mitigation')})"), '', '## Verification Strategy', *lines_for(plan.get('verification_strategy', []), lambda item: f'- {item}'), '', '## Rollback Strategy', *lines_for(plan.get('rollback_strategy', []), lambda item: f'- {item}'), '', '## Recommended Proposal Boundaries', '', 'Recommended proposals:', *lines_for(boundaries.get('recommended_proposals', []), lambda item: f'- {item}'), '', 'Do not combine:', *lines_for(boundaries.get('do_not_combine', []), lambda item: f'- {item}'), ''])
    if isinstance(resourcefulness, list) and resourcefulness:
        lines.extend(['## Resourcefulness', ''])
        for item in resourcefulness:
            if not isinstance(item, dict):
                continue
            diagnosis = item.get('diagnosis', {}) if isinstance(item.get('diagnosis'), dict) else {}
            lines.extend([f"- strategy: {item.get('strategy')}", f"- reason: {diagnosis.get('reason')}", '- reconstructed categories:'])
            for category in item.get('categories', [])[:7] if isinstance(item.get('categories', []), list) else []:
                if not isinstance(category, dict):
                    continue
                paths = []
                for path_item in category.get('paths', [])[:2] if isinstance(category.get('paths', []), list) else []:
                    if isinstance(path_item, dict) and path_item.get('path'):
                        paths.append(str(path_item.get('path')))
                lines.append(f"  - {category.get('category')}: {category.get('status')} ({(', '.join(paths) if paths else 'no paths')})")
            lines.append('')
    lines.extend(['## Inspection Sufficiency', '', f"- Sufficient for planning: {assessment.get('sufficient_for_planning')}", f"- Sufficient for proposal: {assessment.get('sufficient_for_proposal')}", f"- Planning confidence: {assessment.get('planning_confidence')}", '', 'Warnings:', *lines_for(assessment.get('warnings', []), lambda item: f'- {item}'), '', '- Coverage summary:', '```json', json.dumps(assessment.get('coverage_summary', {}), indent=2), '```', '', 'Additional inspection recommended:', *lines_for(assessment.get('additional_inspection_recommended', []), lambda item: f'- {item}'), ''])
    return '\n'.join(lines)

def _update_state_after_plan(deps: MissionPlanningDependencies, state_data: dict[str, Any], mission_id: str, plan_path: Path, plan_payload: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    next_action = deps._next_action_after_plan(mission_id, plan_payload, state=state_data)
    readiness = deps._assess_plan_proposal_readiness(plan_payload)
    unresolved: list[str] = []
    for item in state_data.get('unresolved', []):
        text = str(item)
        if text in {'Architecture plan has not been generated.', 'No implementation proposal exists.'}:
            continue
        if text.startswith('Implementation proposal is blocked:'):
            continue
        if text not in unresolved:
            unresolved.append(text)
    if readiness.get('ready'):
        unresolved.append('No implementation proposal exists.')
    else:
        blocked_note = f"Implementation proposal is blocked: {readiness.get('reason')}"
        if blocked_note not in unresolved:
            unresolved.append(blocked_note)
    return {**state_data, 'schema_version': state_data.get('schema_version', deps.MISSION_SCHEMA_VERSION), 'mission_id': mission_id, 'updated_at': created_at, 'phase': 'planned', 'status': 'plan_complete', 'planning_complete': True, 'proposals_complete': False, 'unresolved': unresolved, 'next_action': next_action, 'plan': {'path': deps._stable(plan_path), 'created_at': created_at, 'schema_version': deps.MISSION_SCHEMA_VERSION}}

def _planning_failure(deps: MissionPlanningDependencies, status: str, mission_id: str | None, reason: str, *, next_action: dict[str, Any] | None=None, extra: dict[str, Any] | None=None, exit_code: int=1) -> int:
    payload = {'ok': False, 'status': status, 'error': status, 'mission_id': mission_id, 'reason': reason, 'authority': 'planning_synthesis_only', 'source_files_modified': False}
    if next_action:
        payload['next_action'] = next_action
    if extra:
        payload.update(extra)
    deps.emit(payload)
    return exit_code

def _execute_mission_planning(deps: MissionPlanningDependencies, mission_dir: Path, *, command_label: str, result_status: str, extra_payload: dict[str, Any] | None=None) -> int:
    mission_id = mission_dir.name
    plan_json_path = deps._mission_plan_json_path(mission_dir)
    plan_md_path = _mission_plan_md_path(deps, mission_dir)
    try:
        artifacts = _load_mission_artifacts(deps, mission_dir)
    except ValueError as exc:
        return _planning_failure(deps, 'invalid_mission_artifact', mission_id, str(exc), exit_code=2)
    evidence = _normalize_inspection_evidence(deps, artifacts)
    readiness = _assess_planning_readiness(deps, artifacts, evidence)
    next_inspect = {'command': mission_command('inspect', mission_id), 'authority': 'read_only_inspection'}
    if not readiness.get('ready'):
        return _planning_failure(deps, 'planning_not_ready', mission_id, str(readiness.get('reason') or 'Inspection evidence is insufficient.'), next_action=next_inspect, exit_code=1)
    ready, model_server_status, _started_model_server = deps._require_model_ready(start_model_server=False)
    if not ready:
        return _planning_failure(deps, 'model_inference_failed', mission_id, 'Model server is not ready for mission planning.', extra={'model_server_status': model_server_status}, exit_code=1)
    planning_context = _build_planning_context(
        artifacts,
        evidence,
        readiness,
        inspection_classes=deps.INSPECTION_CLASSES,
        coverage_categories=deps.MISSION_COVERAGE_CATEGORIES,
        next_files=deps._dedupe_manifest_paths(
            artifacts.get("manifest", {}).get("files_remaining", [])
        ),
        resourcefulness_context=compact_resourcefulness_context(artifacts),
    )
    try:
        prompt, prompt_metadata = build_planning_prompt(planning_context)
    except PlanningPromptBudgetError as exc:
        return _planning_failure(
            deps,
            'planning_prompt_budget_exceeded',
            mission_id,
            str(exc),
            extra={
                'resourcefulness_compression_diagnostics': exc.diagnostics,
            },
            exit_code=1,
        )
    planning_context.update(prompt_metadata)
    model_response = deps._call_model(prompt, _planning_system_context(deps), deps.PLAN_MAX_NEW_TOKENS)
    draft = str(model_response.get('draft') or '').strip()
    if not model_response.get('ok') or model_response.get('status') != 'draft_generated' or (not draft):
        return _planning_failure(deps, 'model_inference_failed', mission_id, 'Planning model did not return a usable draft.', extra={'model_response': model_response, 'model_server_status': model_server_status}, exit_code=1)
    parsed_model_plan = deps._parse_model_json_object(draft)
    if parsed_model_plan is None:
        return _planning_failure(deps, 'invalid_plan_response', mission_id, 'Planning model response was not valid JSON.', extra={'model_response_status': model_response.get('status'), 'model_draft_excerpt': draft[:1200]}, exit_code=1)
    created_at = deps._now()
    plan_payload = _normalize_plan_payload(deps, parsed_model_plan, artifacts, evidence, created_at=created_at)
    resourcefulness_diagnostics = prompt_metadata.get('resourcefulness_compression_diagnostics')
    if isinstance(resourcefulness_diagnostics, dict) and resourcefulness_diagnostics:
        plan_payload['resourcefulness_compression_diagnostics'] = resourcefulness_diagnostics
    validation_errors = _validate_plan_payload(deps, plan_payload, evidence)
    if validation_errors:
        return _planning_failure(deps, 'invalid_plan_response', mission_id, 'Normalized plan failed validation.', extra={'validation_errors': validation_errors}, exit_code=1)
    plan_dir = deps._mission_plan_dir(mission_dir)
    try:
        plan_dir.mkdir(parents=True, exist_ok=True)
        deps._atomic_json(plan_json_path, plan_payload)
        deps._atomic_text(plan_md_path, _render_plan_markdown(deps, plan_payload))
        state_payload = _update_state_after_plan(deps, artifacts['state'], mission_id, plan_json_path, plan_payload, created_at=created_at)
        deps._atomic_json(deps._mission_state_path(mission_dir), state_payload)
    except Exception as exc:
        return _planning_failure(deps, 'plan_write_failed', mission_id, f'{type(exc).__name__}: {exc}', exit_code=1)
    observation = {'command': command_label, 'status': result_status, 'mission_id': mission_id, 'plan_path': deps._stable(plan_json_path), 'markdown_path': deps._stable(plan_md_path), 'source_files_modified': False, 'authority': 'planning_synthesis_only'}
    deps._append_mission_event(mission_dir, 'planned', observation)
    deps.refresh_pinboard(mission=str(artifacts['intent'].get('intent') or mission_id), last_observation=observation, next_action=state_payload['next_action'])
    payload = {'ok': True, 'status': result_status, 'mission_id': mission_id, 'plan_path': deps._stable(plan_json_path), 'markdown_path': deps._stable(plan_md_path), 'findings': len(plan_payload.get('causal_findings', [])), 'unresolved_questions': len(plan_payload.get('unresolved_questions', [])), 'next_action': state_payload['next_action'], 'source_files_modified': False, 'authority': 'planning_synthesis_only'}
    if extra_payload:
        payload.update(extra_payload)
    deps.emit(payload)
    return 0

def run_mission_plan(deps: MissionPlanningDependencies, mission_reference: str | None) -> int:
    try:
        mission_dir = deps._resolve_mission_dir(mission_reference)
    except ValueError as exc:
        return _planning_failure(deps, 'mission_not_found', str(mission_reference), str(exc), exit_code=2)
    mission_id = mission_dir.name
    plan_json_path = deps._mission_plan_json_path(mission_dir)
    plan_md_path = _mission_plan_md_path(deps, mission_dir)
    if plan_json_path.exists() or plan_md_path.exists():
        payload = {'ok': False, 'status': 'plan_already_exists', 'mission_id': mission_id, 'plan_path': deps._stable(plan_json_path), 'markdown_path': deps._stable(plan_md_path), 'authority': 'planning_synthesis_only', 'source_files_modified': False}
        deps.emit(payload)
        return 0
    return _execute_mission_planning(deps, mission_dir, command_label='mission plan', result_status='plan_complete')

def run_mission_replan(deps: MissionPlanningDependencies, mission_reference: str | None) -> int:
    try:
        mission_dir = deps._resolve_mission_dir(mission_reference)
    except ValueError as exc:
        return _planning_failure(deps, 'mission_not_found', str(mission_reference), str(exc), exit_code=2)
    mission_id = mission_dir.name
    plan_json_path = deps._mission_plan_json_path(mission_dir)
    plan_md_path = _mission_plan_md_path(deps, mission_dir)
    if not plan_json_path.exists() and (not plan_md_path.exists()):
        return _planning_failure(deps, 'plan_required_for_replan', mission_id, 'mission replan requires an existing plan artifact to replace.', exit_code=1)
    proposal_json_path = deps._mission_proposal_json_path(mission_dir)
    proposal_md_path = deps._mission_proposal_md_path(mission_dir)
    if proposal_json_path.exists() or proposal_md_path.exists():
        payload = {'ok': False, 'status': 'replan_blocked_proposal_exists', 'error': 'replan_blocked_proposal_exists', 'mission_id': mission_id, 'reason': 'mission replan is only permitted before proposal artifacts exist.', 'proposal_path': deps._stable(proposal_json_path), 'markdown_path': deps._stable(proposal_md_path), 'authority': 'planning_synthesis_only', 'source_files_modified': False}
        deps.emit(payload)
        return 1
    return _execute_mission_planning(deps, mission_dir, command_label='mission replan', result_status='replan_complete')


def execute_mission_planning(
    deps: MissionPlanningDependencies,
    mission_dir: Path,
    *,
    command_label: str,
    result_status: str,
    extra_payload: dict[str, Any] | None = None,
) -> int:
    return _execute_mission_planning(
        deps,
        mission_dir,
        command_label=command_label,
        result_status=result_status,
        extra_payload=extra_payload,
    )