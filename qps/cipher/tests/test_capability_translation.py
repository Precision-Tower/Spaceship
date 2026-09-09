from pathlib import Path

from qps.cipher.foreign.capability_discovery import (
    collapse_python_capability_discovery,
    discover_python_capability_graph,
)
from qps.cipher.foreign.capability_graph import CapabilityIdentity
from qps.cipher.foreign.capability_translation import (
    translate_python_capability,
)


def _prove(identity: CapabilityIdentity):
    discovery = discover_python_capability_graph((identity,))
    assert not discovery.blockers
    assert len(discovery.graph.nodes) == 1

    before = collapse_python_capability_discovery(
        discovery,
        workspace_root=Path.cwd(),
    )
    assert not before.result.ready
    assert before.result.dispositions[identity].detail == (
        "translated-and-validated proof required"
    )

    translated = translate_python_capability(
        discovery.resolved[identity],
        workspace_root=Path.cwd(),
    )
    assert translated.candidate

    after = collapse_python_capability_discovery(
        discovery,
        workspace_root=Path.cwd(),
        translated_proofs={identity: translated},
    )
    assert after.result.ready
    assert after.result.dispositions[identity].state == "proven"
    return translated


def test_real_external_leaf_requires_translation_validation_proof():
    translated = _prove(
        CapabilityIdentity(
            "sniffio._version",
            ("__version__",),
        )
    )
    assert '__version__- "1.3.1"/a;' in translated.candidate


def test_real_stdlib_leaf_requires_translation_validation_proof():
    translated = _prove(
        CapabilityIdentity(
            "string",
            ("digits",),
        )
    )
    assert "digits-" in translated.candidate


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    failures = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append((test.__name__, exc))
    for name, exc in failures:
        print(f"FAIL {name}: {exc}")
    print(
        "CAPABILITY_TRANSLATION_TEST_SUMMARY "
        f"tests={len(tests)} failures={len(failures)}"
    )
    raise SystemExit(1 if failures else 0)


def test_translated_capability_preserves_original_source_provenance():
    from pathlib import Path
    from qps.cipher.foreign.capability_discovery import (
        discover_python_capability_graph,
    )
    from qps.cipher.foreign.capability_graph import CapabilityIdentity
    from qps.cipher.foreign.capability_translation import (
        translate_python_capability,
    )

    identity = CapabilityIdentity(
        "sniffio._version",
        ("__version__",),
    )
    discovery = discover_python_capability_graph((identity,))
    resolved = discovery.resolved[identity]
    translated = translate_python_capability(
        resolved,
        workspace_root=Path.cwd(),
    )

    assert str(resolved.capability_source.source) in translated.candidate
    assert translated.source == resolved.capability_source.source
