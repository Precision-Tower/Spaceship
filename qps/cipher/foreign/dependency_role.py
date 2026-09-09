from __future__ import annotations

from dataclasses import dataclass

from qps.cipher.ir.nodes import DependencyRef


@dataclass(frozen=True)
class DependencyRole:
    dependency: DependencyRef
    role: str
    reason: str


SOURCE_ONLY_PYTHON_SYMBOLS = {
    ("dataclasses", "dataclass"):
        "Python dataclass decorator affects source structure but is not required after value-structure lowering",

    ("dataclasses", "field"):
        "Python dataclass field metadata/default factory is source construction machinery",

    ("typing", "Any"):
        "Python typing annotation has no required runtime meaning in emitted QPS",
}


def classify_dependency_role(
    dependency: DependencyRef,
) -> DependencyRole:
    module = (
        dependency.module
        or dependency.package
        or ""
    )

    key = (
        module,
        dependency.symbol,
    )

    reason = SOURCE_ONLY_PYTHON_SYMBOLS.get(key)

    if reason is not None:
        return DependencyRole(
            dependency=dependency,
            role="source-only",
            reason=reason,
        )

    return DependencyRole(
        dependency=dependency,
        role="library",
        reason=(
            "Dependency contributes runtime or unresolved "
            "external semantics until proven otherwise"
        ),
    )
