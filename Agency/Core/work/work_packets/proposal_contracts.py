from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ProposalIntentKind(str, Enum):
    REPLACE_TEXT = "replace_text"
    CREATE_FILE = "create_file"
    WRITE_FILE = "write_file"
    APPLY_PATCH = "apply_patch"


PROPOSAL_CAPABILITIES: dict[ProposalIntentKind, dict[str, Any]] = {
    ProposalIntentKind.REPLACE_TEXT: {
        "enabled": True,
        "syntax": 'replace "<old>" with "<new>" in <path>',
        "description": "Produce a read-only patch proposal.",
    },
    ProposalIntentKind.CREATE_FILE: {
        "enabled": False,
        "syntax": "create file <path> containing exactly <content>",
        "description": "Recognized by the parser but not yet enabled.",
    },
    ProposalIntentKind.WRITE_FILE: {
        "enabled": False,
        "syntax": "write file <path> containing exactly <content>",
        "description": "Recognized by the parser but not yet enabled.",
    },
    ProposalIntentKind.APPLY_PATCH: {
        "enabled": False,
        "syntax": "apply patch from <path>",
        "description": "Recognized by the parser but not yet enabled.",
    },
}


def proposal_capability(
    intent_kind: ProposalIntentKind,
) -> dict[str, Any]:
    return dict(PROPOSAL_CAPABILITIES[intent_kind])


@dataclass(frozen=True)
class ProposalScope:
    include: tuple[str, ...]
    exclude: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "include": list(self.include),
            "exclude": list(self.exclude),
        }


@dataclass(frozen=True)
class ReplaceText:
    path: str
    old: str
    new: str
    kind: ProposalIntentKind = field(
        default=ProposalIntentKind.REPLACE_TEXT,
        init=False,
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass(frozen=True)
class CreateFile:
    path: str
    content: str
    kind: ProposalIntentKind = field(
        default=ProposalIntentKind.CREATE_FILE,
        init=False,
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass(frozen=True)
class WriteFile:
    path: str
    content: str
    kind: ProposalIntentKind = field(
        default=ProposalIntentKind.WRITE_FILE,
        init=False,
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass(frozen=True)
class ApplyPatch:
    patch_path: str
    kind: ProposalIntentKind = field(
        default=ProposalIntentKind.APPLY_PATCH,
        init=False,
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


ProposalIntent = ReplaceText | CreateFile | WriteFile | ApplyPatch


@dataclass(frozen=True)
class ProposalRequest:
    intent: ProposalIntent
    scope: ProposalScope
    constraints: dict[str, Any] = field(default_factory=dict)
    acceptance_criteria: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "scope": self.scope.to_dict(),
            "constraints": dict(self.constraints),
            "acceptance_criteria": list(self.acceptance_criteria),
        }


def validate_proposal_request(request: ProposalRequest) -> list[str]:
    errors: list[str] = []

    if not request.scope.include:
        errors.append("proposal_scope_required")

    for value in request.scope.include:
        if not str(value).strip():
            errors.append("proposal_scope_contains_empty_path")

    intent = request.intent

    if isinstance(intent, ReplaceText):
        if not intent.path.strip():
            errors.append("replace_text_path_required")
        if not intent.old:
            errors.append("replace_text_old_required")
        if intent.old == intent.new:
            errors.append("replace_text_must_change_content")

    elif isinstance(intent, (CreateFile, WriteFile)):
        if not intent.path.strip():
            errors.append(f"{intent.kind.value}_path_required")

    elif isinstance(intent, ApplyPatch):
        if not intent.patch_path.strip():
            errors.append("apply_patch_path_required")

    else:
        errors.append("unknown_proposal_intent")

    return errors
