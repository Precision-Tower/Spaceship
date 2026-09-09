from pathlib import Path
import tempfile

from qps.cipher.foreign.capability_catalog import (
    CapabilityProof,
    CapabilityProofCatalog,
    make_proof_key,
)
from qps.cipher.foreign.capability_discovery import (
    discover_python_capability_graph,
)
from qps.cipher.foreign.capability_graph import CapabilityIdentity


def test_real_stdlib_capability_discovers_same_module_closure():
    result = discover_python_capability_graph(
        (CapabilityIdentity("statistics", ("mean",)),),
    )
    names = {item.canonical for item in result.graph.nodes}
    assert "statistics.mean" in names
    assert "statistics._sum" in names
    assert "statistics._convert" in names
    assert result.graph.depth >= 2


def test_real_external_capability_discovers_exact_reexport_and_impl():
    result = discover_python_capability_graph(
        (CapabilityIdentity("sniffio", ("current_async_library",)),),
    )
    names = {item.canonical for item in result.graph.nodes}
    assert "sniffio.current_async_library" in names
    assert "sniffio._impl.current_async_library" in names
    assert "sniffio._impl.thread_local" in names
    assert "sniffio._impl.current_async_library_cvar" in names


def test_native_importlib_evidence_is_not_treated_as_native_proof():
    result = discover_python_capability_graph(
        (CapabilityIdentity("sys", ("modules",)),),
    )
    boundary = result.boundaries[CapabilityIdentity("sys", ("modules",))]
    assert boundary.kind == "native-proof-required"
    assert CapabilityIdentity("sys", ("modules",)) in result.blockers


def test_missing_optional_dependency_is_unresolved_not_native():
    result = discover_python_capability_graph(
        (CapabilityIdentity("curio.meta", ("curio_running",)),),
    )
    boundary = result.boundaries[
        CapabilityIdentity("curio.meta", ("curio_running",))
    ]
    assert boundary.kind == "unresolved"

def test_collapse_propagates_real_unresolved_external_blocker():
    from qps.cipher.foreign.capability_discovery import (
        collapse_python_capability_discovery,
    )

    root = CapabilityIdentity("sniffio", ("current_async_library",))
    discovery = discover_python_capability_graph((root,))
    collapsed = collapse_python_capability_discovery(
        discovery,
        workspace_root=Path.cwd(),
    )
    assert not collapsed.result.ready
    assert root in collapsed.result.blockers
    curio = CapabilityIdentity("curio.meta", ("curio_running",))
    assert curio in collapsed.result.causal_blockers(root)


def test_importlib_native_boundary_cannot_collapse_without_exact_native_proof():
    from qps.cipher.foreign.capability_discovery import (
        collapse_python_capability_discovery,
    )

    root = CapabilityIdentity("sys", ("modules",))
    discovery = discover_python_capability_graph((root,))
    collapsed = collapse_python_capability_discovery(
        discovery,
        workspace_root=Path.cwd(),
    )
    assert not collapsed.result.ready
    assert root in collapsed.result.blockers
    assert root not in collapsed.native_proven

def test_authored_usage_drives_only_used_external_capability():
    from qps.cipher.foreign.capability_discovery import (
        discover_authored_python_capabilities,
    )

    result = discover_authored_python_capabilities(
        "import sniffio\n"
        "value = sniffio.current_async_library()\n"
    )
    assert result.discovery is not None
    roots = [
        item.canonical
        for item in result.discovery.graph.roots
    ]
    assert roots == ["sniffio.current_async_library"]
    assert "sniffio.current_async_library" in {
        item.canonical for item in result.discovery.graph.nodes
    }


def test_authored_dynamic_ambiguity_stops_before_graph_expansion():
    from qps.cipher.foreign.capability_discovery import (
        discover_authored_python_capabilities,
    )

    result = discover_authored_python_capabilities(
        "import sniffio\n"
        "value = getattr(sniffio, runtime_name)\n"
    )
    assert result.discovery is None
    assert result.blockers == (
        "dynamic getattr on bound namespace@2",
    )

if __name__ == "__main__":
    tests = [
        value for name, value in sorted(globals().items())
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
        f"CAPABILITY_DISCOVERY_TEST_SUMMARY "
        f"tests={len(tests)} failures={len(failures)}"
    )
    raise SystemExit(1 if failures else 0)


def test_proven_closure_can_be_stored_and_reused():
    from pathlib import Path
    import tempfile

    from qps.cipher.foreign.capability_catalog import (
        CapabilityProofCatalog,
    )
    from qps.cipher.foreign.capability_discovery import (
        collapse_python_capability_discovery,
        discover_python_capability_graph,
        store_proven_capability_closures,
    )
    from qps.cipher.foreign.capability_graph import CapabilityIdentity
    from qps.cipher.foreign.capability_translation import (
        translate_python_capability,
    )

    identity = CapabilityIdentity(
        "sniffio._version",
        ("__version__",),
    )
    semantic_paths = (
        Path("qps/cipher/foreign/capability_graph.py"),
        Path("qps/cipher/foreign/capability_discovery.py"),
        Path("qps/cipher/foreign/capability_translation.py"),
    )

    with tempfile.TemporaryDirectory(
        dir=Path("trash/tmp"),
    ) as raw:
        catalog_path = Path(raw) / "catalog.json"
        catalog = CapabilityProofCatalog(catalog_path)

        first = discover_python_capability_graph(
            (identity,),
            catalog=catalog,
            semantic_paths=semantic_paths,
        )
        translated = translate_python_capability(
            first.resolved[identity],
            workspace_root=Path.cwd(),
        )
        collapse = collapse_python_capability_discovery(
            first,
            workspace_root=Path.cwd(),
            translated_proofs={identity: translated},
        )
        assert collapse.result.ready

        stored = store_proven_capability_closures(
            first,
            collapse,
            catalog,
            semantic_paths=semantic_paths,
        )
        assert stored == (identity,)

        reopened = CapabilityProofCatalog(catalog_path)
        second = discover_python_capability_graph(
            (identity,),
            catalog=reopened,
            semantic_paths=semantic_paths,
        )
        assert identity in second.catalog_hits
        assert second.graph.nodes[identity].requires == set()

def test_capability_proof_is_persisted_only_after_successful_publication():
    import os
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from qps.cipher.foreign.capability_catalog import CapabilityProofCatalog
    from qps.cipher.foreign.capability_discovery import (
        collapse_python_capability_discovery,
        discover_python_capability_graph,
        publish_proven_capability_transaction,
    )
    from qps.cipher.foreign.capability_graph import CapabilityIdentity
    from qps.cipher.foreign.capability_translation import (
        translate_python_capability,
    )
    from qps.cipher.foreign.population import (
        plan_python_library_capability,
    )
    from qps.cipher.ir.nodes import DependencyRef

    repo = Path(__file__).resolve()
    while repo != repo.parent and not (repo / ".git").exists():
        repo = repo.parent
    os.environ["QPS_EXECUTABLE"] = str(repo / "qps/cpp/build-pixel/qps")

    identity = CapabilityIdentity(
        "sniffio._version",
        ("__version__",),
    )
    semantic_paths = (
        repo / "qps/cipher/_index.qps",
        repo / "qps/qps/cipher.qps",
    )

    with TemporaryDirectory(dir=os.environ.get("TMPDIR")) as raw:
        root = Path(raw)
        libs = root / "libs/Python"
        libs.mkdir(parents=True)
        (libs / "_index.qps").write_text(
            "Python.\n\nsurface: (\n);\n",
            encoding="utf-8",
        )

        catalog_path = root / "catalog.json"
        catalog = CapabilityProofCatalog(catalog_path)
        discovery = discover_python_capability_graph(
            (identity,),
            semantic_paths=semantic_paths,
        )
        translated = translate_python_capability(
            discovery.resolved[identity],
            workspace_root=repo,
        )
        collapse = collapse_python_capability_discovery(
            discovery,
            workspace_root=repo,
            translated_proofs={identity: translated},
        )
        assert collapse.result.ready

        dependency = DependencyRef(
            package="sniffio",
            module="sniffio._version",
            symbol=None,
        )
        plan = plan_python_library_capability(
            dependency,
            root,
            identity.members,
            translated.candidate,
        )

        try:
            publish_proven_capability_transaction(
                plan,
                discovery,
                collapse,
                catalog,
                semantic_paths=semantic_paths,
                fail_after=1,
            )
        except RuntimeError as exc:
            assert "injected library publication failure" in str(exc)
        else:
            raise AssertionError("publication failure injection did not fire")

        assert not catalog_path.exists(), (
            "failed publication created reusable catalog proof"
        )

        published, stored = publish_proven_capability_transaction(
            plan,
            discovery,
            collapse,
            catalog,
            semantic_paths=semantic_paths,
        )
        assert published
        assert identity in stored
        assert catalog_path.exists()

        reopened = CapabilityProofCatalog(catalog_path)
        reused = discover_python_capability_graph(
            (identity,),
            catalog=reopened,
            semantic_paths=semantic_paths,
        )
        assert identity in reused.catalog_hits
