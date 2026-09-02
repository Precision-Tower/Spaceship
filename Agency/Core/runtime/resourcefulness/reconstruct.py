from __future__ import annotations

from typing import Any

from .strategy import ResourcefulnessContext, ResourcefulnessResult


def _observation_sort_key(item: dict[str, Any]) -> tuple[int, int, str, str]:
    priority = {
        "file_inspected": 0,
        "symbol": 1,
        "dependency": 2,
        "pass_observation": 3,
    }
    return (
        priority.get(str(item.get("kind") or ""), 9),
        int(item.get("pass") or 0),
        str(item.get("path") or ""),
        str(item.get("id") or ""),
    )


def _observation_ref(item: dict[str, Any]) -> dict[str, Any]:
    ref = {
        "observation_id": item.get("id"),
        "kind": item.get("kind"),
        "pass": item.get("pass"),
        "path": item.get("path"),
    }
    name = str(item.get("name") or "").strip()
    target = str(item.get("target") or "").strip()
    if name:
        ref["name"] = name
    if target:
        ref["target"] = target
    return ref


class ReconstructStrategy:
    def name(self) -> str:
        return "reconstruct"

    def can_execute(self, context: ResourcefulnessContext) -> bool:
        if bool(context.proposal_readiness.get("ready")):
            return False
        observations = context.evidence.get("observations", [])
        return isinstance(observations, list) and any(
            isinstance(item, dict) and str(item.get("id") or "")
            for item in observations
        )

    def execute(self, context: ResourcefulnessContext) -> ResourcefulnessResult:
        reconstruction = self._build_reconstruction(context)
        return ResourcefulnessResult(
            strategy=self.name(),
            status="resourcefulness_reconstruction_complete",
            reason="Reconstructed architecture evidence from existing inspection observations.",
            artifacts={"resourcefulness_reconstruction": reconstruction},
            confidence="medium",
            next_recommendation="replan",
        )

    def _build_reconstruction(self, context: ResourcefulnessContext) -> dict[str, Any]:
        evidence = context.evidence
        artifacts = context.artifacts
        observations = [
            item for item in evidence.get("observations", [])
            if isinstance(item, dict) and str(item.get("id") or "")
        ]
        by_path: dict[str, list[dict[str, Any]]] = {}
        for item in observations:
            path = str(item.get("path") or "").strip()
            if path:
                by_path.setdefault(path, []).append(item)
        for path_items in by_path.values():
            path_items.sort(key=_observation_sort_key)

        def path_score(path: str) -> tuple[int, int, str]:
            path_items = by_path.get(path, [])
            kinds = {str(item.get("kind") or "") for item in path_items}
            has_structural_signal = bool({"symbol", "dependency"}.intersection(kinds))
            has_primary_file = any(
                item.get("kind") == "file_inspected" and item.get("class") == "primary"
                for item in path_items
            )
            earliest_pass = min((int(item.get("pass") or 0) for item in path_items), default=9999)
            if has_structural_signal:
                rank = 0
            elif has_primary_file:
                rank = 1
            else:
                rank = 2
            return (rank, earliest_pass, path)

        coverage_evidence = evidence.get("coverage_evidence", {})
        if not isinstance(coverage_evidence, dict):
            coverage_evidence = {}
        coverage_summary = evidence.get("coverage_summary", {})
        if not isinstance(coverage_summary, dict):
            coverage_summary = {}

        architecture_evidence: dict[str, Any] = {}
        for category in context.coverage_categories:
            raw_items = coverage_evidence.get(category, [])
            candidates: list[dict[str, str]] = []
            seen_paths: set[str] = set()
            if isinstance(raw_items, list):
                for raw in raw_items:
                    if not isinstance(raw, dict):
                        continue
                    raw_path = str(raw.get("path") or "").strip()
                    if not raw_path or raw_path in seen_paths:
                        continue
                    seen_paths.add(raw_path)
                    candidates.append({
                        "path": raw_path,
                        "reason": str(raw.get("reason") or "inspection coverage evidence"),
                    })
            records: list[dict[str, Any]] = []
            for raw in sorted(candidates, key=lambda item: path_score(item["path"]))[:6]:
                path_items = by_path.get(raw["path"], [])[:5]
                records.append({
                    "path": raw["path"],
                    "reason": raw["reason"],
                    "signals": sorted({str(item.get("kind") or "") for item in path_items if item.get("kind")}),
                    "observations": [_observation_ref(item) for item in path_items],
                })
            architecture_evidence[category] = {
                "status": str(coverage_summary.get(category) or "not_started"),
                "paths": records,
            }

        coverage_paths = {
            record["path"]
            for category in architecture_evidence.values()
            for record in category.get("paths", [])
            if isinstance(record, dict) and record.get("path")
        }
        relationships: list[dict[str, Any]] = []
        for item in sorted(observations, key=_observation_sort_key):
            if item.get("kind") != "dependency":
                continue
            source = str(item.get("path") or "").strip()
            target = str(item.get("target") or "").strip()
            if not source or not target:
                continue
            if source not in coverage_paths and target not in coverage_paths:
                continue
            relationships.append({
                "source": source,
                "target": target,
                "observation_id": item.get("id"),
                "pass": item.get("pass"),
            })
            if len(relationships) >= 18:
                break

        unresolved: list[str] = []
        for item in context.plan.get("unresolved_questions", []):
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            if question and question not in unresolved:
                unresolved.append(question)
            if len(unresolved) >= 8:
                break
        for item in evidence.get("coverage_unresolved", [])[:8]:
            question = str(item).strip()
            if question and question not in unresolved:
                unresolved.append(question)

        return {
            "schema_version": context.schema_version,
            "mission_id": context.mission_id,
            "created_at": context.created_at,
            "strategy": self.name(),
            "authority": "bounded_self_diagnosis_from_existing_inspection",
            "source_files_modified": False,
            "diagnosis": {
                "proposal_ready": bool(context.proposal_readiness.get("ready")),
                "reason": str(context.proposal_readiness.get("reason") or "proposal readiness is false"),
                "inspection_complete": bool(artifacts.get("coverage", {}).get("inspection_complete", False)),
                "inspection_passes": len(artifacts.get("passes", [])),
                "files_inspected": len(evidence.get("files_inspected", [])),
                "observations": len(observations),
            },
            "architecture_evidence": architecture_evidence,
            "relationships": relationships,
            "unresolved": unresolved,
        }
