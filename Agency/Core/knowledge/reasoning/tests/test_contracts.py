from Agency.Core.knowledge.reasoning import (
    first_evidence_ref,
    normalize_evidence_refs,
)

from Agency.Core.knowledge.reasoning import (
    CausalFinding,
    EvidenceReference,
    ReasoningAssumption,
    ReasoningResult,
    SystemModel,
    UnresolvedQuestion,
)


def test_reasoning_result_serializes_existing_planning_vocabulary() -> None:
    result = ReasoningResult(
        objective="Explain the repository execution path.",
        current_system_model=SystemModel(
            components=("repository inspector", "model runtime"),
            control_flow=("inspection -> evidence -> reasoning",),
            state_ownership=("repository inspector owns evidence",),
            integration_points=("model_service.py",),
        ),
        causal_findings=(
            CausalFinding(
                finding_id="finding-001",
                claim="Repository inspection currently stops before inference.",
                evidence=(
                    EvidenceReference(
                        observation_id="observation-001",
                        path="Agency/Core/runtime/model_service.py",
                        inspection_pass=1,
                    ),
                ),
                confidence="high",
            ),
        ),
        assumptions=(
            ReasoningAssumption(
                assumption_id="assumption-001",
                statement="The existing model runtime can consume a compact prompt.",
                reason="Mission Planning already invokes it this way.",
                risk_if_false="A separate inference adapter would be required.",
            ),
        ),
        unresolved_questions=(
            UnresolvedQuestion(
                unresolved_id="unresolved-001",
                question="Which runtime adapter should own model invocation?",
                blocking=False,
            ),
        ),
        recommended_next_actions=(
            "Extract evidence-reference normalization.",
        ),
    )

    payload = result.to_dict()

    assert payload["authority"] == "reasoning_only"
    assert payload["causal_findings"][0]["evidence"][0] == {
        "observation_id": "observation-001",
        "path": "Agency/Core/runtime/model_service.py",
        "pass": 1,
    }
    assert payload["assumptions"][0]["id"] == "assumption-001"
    assert payload["unresolved_questions"][0]["blocking"] is False

def test_normalize_evidence_refs_rejects_unknown_observations() -> None:
    evidence = {
        "observations_by_id": {
            "observation-001": {
                "id": "observation-001",
                "path": "Agency/Core/runtime/model_service.py",
                "pass": 2,
            }
        }
    }

    refs = normalize_evidence_refs(
        [
            "observation-001",
            {"observation_id": "missing"},
            42,
        ],
        evidence,
    )

    assert [ref.to_dict() for ref in refs] == [
        {
            "observation_id": "observation-001",
            "path": "Agency/Core/runtime/model_service.py",
            "pass": 2,
        }
    ]


def test_first_evidence_ref_skips_unusable_observations() -> None:
    evidence = {
        "observations": [
            {
                "id": "observation-001",
                "path": None,
                "pass": 1,
            },
            {
                "id": "observation-002",
                "path": "Agency/Core/repository/context/builder.py",
                "pass": 3,
            },
        ]
    }

    ref = first_evidence_ref(evidence)

    assert ref is not None
    assert ref.to_dict() == {
        "observation_id": "observation-002",
        "path": "Agency/Core/repository/context/builder.py",
        "pass": 3,
    }
