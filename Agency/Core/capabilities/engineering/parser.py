from __future__ import annotations

import ast
import re

from Agency.Core.work.work_packets.proposal_contracts import (
    ApplyPatch,
    CreateFile,
    ProposalRequest,
    ProposalScope,
    ReplaceText,
    WriteFile,
)


REPLACE_RE = re.compile(
    r"^\s*replace\s+"
    r"(?P<old>'[^']*'|\"[^\"]*\")\s+"
    r"with\s+"
    r"(?P<new>'[^']*'|\"[^\"]*\")\s+"
    r"in\s+"
    r"(?P<path>[^\s]+)\s*$",
    re.IGNORECASE | re.DOTALL,
)

CREATE_OR_WRITE_RE = re.compile(
    r"^\s*(?P<verb>create|write)(?:\s+file)?\s+"
    r"(?P<path>[^\s]+)\s+containing"
    r"(?:\s+exactly)?\s+"
    r"(?P<content>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)

PATCH_RE = re.compile(
    r"^\s*(?:propose|apply)\s+patch"
    r"(?:\s+from)?\s+"
    r"(?P<path>[^\s]+)\s*$",
    re.IGNORECASE,
)


class EngineeringParser:
    @staticmethod
    def parse(prompt: str) -> ProposalRequest:
        text = str(prompt or "").strip()
        if not text:
            raise ValueError("engineering_prompt_required")

        replace_match = REPLACE_RE.fullmatch(text)
        if replace_match:
            try:
                old = ast.literal_eval(replace_match.group("old"))
                new = ast.literal_eval(replace_match.group("new"))
            except Exception as exc:
                raise ValueError(
                    "invalid_replace_text_literal"
                ) from exc

            path = replace_match.group("path").rstrip(".,;:")
            return ProposalRequest(
                intent=ReplaceText(
                    path=path,
                    old=str(old),
                    new=str(new),
                ),
                scope=ProposalScope(include=(path,)),
            )

        file_match = CREATE_OR_WRITE_RE.fullmatch(text)
        if file_match:
            verb = file_match.group("verb").lower()
            path = file_match.group("path")
            content = file_match.group("content")

            intent = (
                CreateFile(path=path, content=content)
                if verb == "create"
                else WriteFile(path=path, content=content)
            )

            return ProposalRequest(
                intent=intent,
                scope=ProposalScope(include=(path,)),
            )

        patch_match = PATCH_RE.fullmatch(text)
        if patch_match:
            path = patch_match.group("path")
            return ProposalRequest(
                intent=ApplyPatch(patch_path=path),
                scope=ProposalScope(include=(".",)),
                constraints={
                    "max_files": 100,
                    "max_matches": 1000,
                    "max_total_context_bytes": 1_000_000,
                },
            )

        raise ValueError("unsupported_engineering_proposal_syntax")
