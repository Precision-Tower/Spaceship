from __future__ import annotations

import json
from pathlib import Path

from ..ir.document import CipherDocument
from .provenance_qps import (
    emit_source_provenance,
    source_artifact_for_path,
    stable_source_path,
)
from ..mapping.dependencies import resolve_symbols
from ..mapping.geometry import geometry_capabilities


def _q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _safe_identity(value: str) -> str:
    result = []

    for char in value:
        if char.isalnum() or char == "_":
            result.append(char)
        else:
            result.append("_")

    identity = "".join(result).strip("_")

    return identity or "capability"


def emit_convergence_qps(
    document: CipherDocument,
    *,
    workspace_root=None,
) -> str:
    resolved = resolve_symbols(document)
    capabilities = geometry_capabilities(document)

    capability_by_source = {
        (
            item.implementation_symbol,
            item.source_path,
            item.source_line,
        ): item
        for item in capabilities
    }

    records = []

    for symbol in resolved:
        implementation_tail = (
            symbol.implementation_symbol
            .replace("::", ".")
            .rsplit(".", 1)[-1]
        )

        capability = capability_by_source.get(
            (
                implementation_tail,
                symbol.source_path,
                symbol.source_line,
            )
        )

        if capability is None:
            continue

        semantic = capability.semantic_name
        identity = _safe_identity(semantic)

        dependency = symbol.dependency

        source_artifact = source_artifact_for_path(
            document,
            symbol.source_path,
        )

        if source_artifact is not None:
            source_family = source_artifact.family
            source_extension = source_artifact.extension
            source_path = stable_source_path(
                source_artifact,
                workspace_root,
            )
        else:
            source_family = (
                symbol.dependency.source.language
                if (
                    symbol.dependency.source is not None
                    and symbol.dependency.source.language
                )
                else "unknown"
            )
            source_extension = (
                Path(symbol.source_path).suffix
                if symbol.source_path
                else ""
            )
            source_path = symbol.source_path

        records.append(
            f'''{identity}: (
source: (
family- {_q(source_family)};
path- {_q(source_path)};
extension- {_q(source_extension)};
line- {symbol.source_line if symbol.source_line is not None else "/n"};
);

dependency: (
package- {_q(dependency.package)};
module- {_q(dependency.module or "")};
symbol- {_q(dependency.symbol or symbol.implementation_symbol)};
alias- {_q(dependency.alias or "")};
);

semantic_identity- {_q(semantic)};
implementation_symbol- {_q(symbol.implementation_symbol)};
translation_state- "mapped";
convergence_state- "candidate";
provenance- "Python import and call resolved to Cipher semantic capability";
);'''
        )

    if not records:
        body = "Cipher_Convergence: (\n);"

        provenance = emit_source_provenance(
            document,
            workspace_root=workspace_root,
        )

        return "\n\n".join(
            section
            for section in (
                provenance,
                body,
            )
            if section
        ) + "\n"

    body = "\n\n".join(
        "    " + record.replace("\n", "\n    ")
        for record in records
    )

    convergence = (
        f"Cipher_Convergence: (\n{body}\n);"
    )

    provenance = emit_source_provenance(
        document,
        workspace_root=workspace_root,
    )

    return "\n\n".join(
        section
        for section in (
            provenance,
            convergence,
        )
        if section
    ) + "\n"
