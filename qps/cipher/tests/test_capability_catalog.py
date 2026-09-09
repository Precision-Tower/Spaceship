from pathlib import Path
import tempfile

from qps.cipher.foreign.capability_catalog import (
    CapabilityProof,
    CapabilityProofCatalog,
    StoredCapabilityIdentity,
    make_proof_key,
)
from qps.cipher.foreign.capability_graph import CapabilityIdentity


def _fixture(directory: Path):
    source = directory / "source.py"
    semantics = directory / "semantics.py"
    source.write_text("def wanted():\n    return 1\n")
    semantics.write_text("SEMANTICS = 1\n")
    identity = CapabilityIdentity("pkg", ("wanted",))
    return source, semantics, identity


def test_catalog_persists_exact_closure_proof():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source, semantics, identity = _fixture(root)
        key = make_proof_key(
            identity,
            source,
            provenance="external-distribution",
            distribution="pkg",
            distribution_version="1.0",
            semantic_paths=(semantics,),
        )
        path = root / "catalog.json"
        catalog = CapabilityProofCatalog(path)
        catalog.store(
            CapabilityProof(
                key,
                "translated-and-validated",
                (
                    StoredCapabilityIdentity(
                        "dep.small",
                        ("member",),
                    ),
                ),
                "qps-check-pass",
                closure=True,
            )
        )
        catalog.publish()

        reopened = CapabilityProofCatalog(path)
        proof = reopened.lookup(key, require_closure=True)
        assert proof is not None
        assert proof.requirements == (
            StoredCapabilityIdentity(
                "dep.small",
                ("member",),
            ),
        )
        assert proof.closure


def test_catalog_source_change_invalidates_lookup():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source, semantics, identity = _fixture(root)
        old_key = make_proof_key(
            identity, source,
            provenance="stdlib",
            distribution=None,
            distribution_version=None,
            semantic_paths=(semantics,),
        )
        catalog = CapabilityProofCatalog(root / "catalog.json")
        catalog.store(
            CapabilityProof(old_key, "proven", (), "pass", closure=True)
        )
        source.write_text("def wanted():\n    return 2\n")
        new_key = make_proof_key(
            identity, source,
            provenance="stdlib",
            distribution=None,
            distribution_version=None,
            semantic_paths=(semantics,),
        )
        assert catalog.lookup(new_key, require_closure=True) is None


def test_catalog_semantics_change_invalidates_lookup():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source, semantics, identity = _fixture(root)
        old_key = make_proof_key(
            identity, source,
            provenance="stdlib",
            distribution=None,
            distribution_version=None,
            semantic_paths=(semantics,),
        )
        catalog = CapabilityProofCatalog(root / "catalog.json")
        catalog.store(
            CapabilityProof(old_key, "proven", (), "pass", closure=True)
        )
        semantics.write_text("SEMANTICS = 2\n")
        new_key = make_proof_key(
            identity, source,
            provenance="stdlib",
            distribution=None,
            distribution_version=None,
            semantic_paths=(semantics,),
        )
        assert catalog.lookup(new_key, require_closure=True) is None


def test_nonclosure_proof_cannot_prune_closure_discovery():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source, semantics, identity = _fixture(root)
        key = make_proof_key(
            identity, source,
            provenance="stdlib",
            distribution=None,
            distribution_version=None,
            semantic_paths=(semantics,),
        )
        catalog = CapabilityProofCatalog(root / "catalog.json")
        catalog.store(
            CapabilityProof(key, "proven", (), "pass", closure=False)
        )
        assert catalog.lookup(key) is not None
        assert catalog.lookup(key, require_closure=True) is None




def test_catalog_preserves_dotted_module_member_boundary():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source, semantics, identity = _fixture(root)
        key = make_proof_key(
            identity,
            source,
            provenance="external-distribution",
            distribution="sniffio",
            distribution_version="1.3.1",
            semantic_paths=(semantics,),
        )
        path = root / "catalog.json"
        catalog = CapabilityProofCatalog(path)
        expected = StoredCapabilityIdentity(
            "sniffio._impl",
            ("current_async_library",),
        )
        catalog.store(
            CapabilityProof(
                key,
                "translated-and-validated",
                (expected,),
                "qps-check-pass",
                closure=True,
            )
        )
        catalog.publish()

        reopened = CapabilityProofCatalog(path)
        proof = reopened.lookup(key, require_closure=True)
        assert proof is not None
        assert proof.requirements == (expected,)
        restored = proof.requirements[0].to_identity()
        assert restored.module == "sniffio._impl"
        assert restored.members == ("current_async_library",)
        assert restored.canonical == (
            "sniffio._impl.current_async_library"
        )


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
        f"CAPABILITY_CATALOG_TEST_SUMMARY "
        f"tests={len(tests)} failures={len(failures)}"
    )
    raise SystemExit(1 if failures else 0)
