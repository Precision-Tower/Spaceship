from qps.cipher.foreign.capability_graph import (
    CapabilityIdentity,
    build_capability_graph,
    discover_used_capabilities,
    discover_capability_usage,
)

def _ids(source: str) -> list[str]:
    return [
        requirement.identity.canonical
        for requirement in discover_used_capabilities(source)
    ]


def test_broad_import_only_requires_used_member():
    assert _ids(
        "import name\n"
        "result = name.sub.foo(value)\n"
    ) == ["name.sub.foo"]


def test_equivalent_import_forms_canonicalize_same_capability():
    sources = [
        "import name\nresult = name.sub.foo(value)\n",
        "import name.sub\nresult = name.sub.foo(value)\n",
        "from name.sub import foo\nresult = foo(value)\n",
        "from name.sub import foo as f\nresult = f(value)\n",
    ]
    assert {_ids(source)[0] for source in sources} == {"name.sub.foo"}


def test_multiple_used_members_do_not_widen_to_package():
    assert _ids(
        "import name\n"
        "a = name.sub.foo(x)\n"
        "b = name.other.bar(y)\n"
    ) == ["name.other.bar", "name.sub.foo"]


def test_unused_import_creates_no_capability_requirement():
    assert _ids("import name\nvalue = 3\n") == []


def test_from_import_used_as_value_is_a_capability():
    assert _ids(
        "from name.sub import CONSTANT\n"
        "value = CONSTANT\n"
    ) == ["name.sub.CONSTANT"]


def test_graph_expands_breadth_first_and_deduplicates_cycle():
    a = CapabilityIdentity("pkg", ("a",))
    b = CapabilityIdentity("pkg", ("b",))
    c = CapabilityIdentity("pkg", ("c",))
    d = CapabilityIdentity("pkg", ("d",))

    edges = {
        a: (b, c),
        b: (d,),
        c: (d,),
        d: (a,),
    }
    graph = build_capability_graph((a,), lambda node: edges[node])

    assert graph.nodes[a].first_tier == 1
    assert graph.nodes[b].first_tier == 2
    assert graph.nodes[c].first_tier == 2
    assert graph.nodes[d].first_tier == 3
    assert graph.depth == 3
    assert [(t.tier, t.encountered, t.new, t.deduplicated) for t in graph.tiers] == [
        (1, 2, 2, 0),
        (2, 2, 1, 1),
        (3, 1, 0, 1),
    ]


def test_graph_saturates_before_returning():
    root = CapabilityIdentity("pkg", ("root",))
    leaf = CapabilityIdentity("pkg", ("leaf",))
    calls = []

    def expand(node):
        calls.append(node.canonical)
        return (leaf,) if node == root else ()

    graph = build_capability_graph((root,), expand)
    assert calls == ["pkg.root", "pkg.leaf"]
    assert graph.tiers[-1].new == 0

def test_imported_capability_used_inside_function_is_discovered():
    assert _ids(
        "import name\n"
        "def run(value):\n"
        "    return name.sub.foo(value)\n"
    ) == ["name.sub.foo"]


def test_import_alias_preserves_canonical_module_identity():
    assert _ids(
        "import name as n\n"
        "value = n.sub.foo(x)\n"
    ) == ["name.sub.foo"]


def test_imported_module_used_as_value_requires_module_capability():
    # Passing the namespace itself is semantically broader than a proven
    # member use, so it must remain visible rather than disappearing.
    assert _ids(
        "import name\n"
        "consume(name)\n"
    ) == ["name"]

def test_capability_source_only_expands_selected_definition(tmp_path=None):
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    source_text = (
        "import dep\n"
        "def wanted(x):\n"
        "    return dep.small(x)\n"
        "def unused(x):\n"
        "    return dep.huge(x)\n"
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(source_text)
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert [item.canonical for item in result.requirements] == ["dep.small"]


def test_capability_source_reports_dynamic_member_access():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(
            "def wanted(obj, member):\n"
            "    return getattr(obj, member)\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert result.dynamic == ("getattr@2",)

def test_capability_source_resolves_absolute_reexport():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "__init__.py"
        path.write_text(
            "from pkg._impl import wanted\n"
            "from pkg._impl import unused\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert result.definition_kind == "reexport"
        assert [item.canonical for item in result.requirements] == [
            "pkg._impl.wanted"
        ]

def test_capability_source_resolves_relative_package_reexport():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "__init__.py"
        path.write_text(
            "from ._impl import wanted\n"
            "from ._impl import unused\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert result.definition_kind == "reexport"
        assert [item.canonical for item in result.requirements] == [
            "pkg._impl.wanted"
        ]


def test_nested_relative_reexport_resolves_parent_package():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "__init__.py"
        path.write_text("from ..shared import wanted\n")
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg.sub", ("wanted",)),
            path,
        )
        assert result is not None
        assert [item.canonical for item in result.requirements] == [
            "pkg.shared.wanted"
        ]

def test_capability_source_reports_conditional_requirements():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(
            "import dep\n"
            "def wanted(flag):\n"
            "    if flag:\n"
            "        return dep.a()\n"
            "    return dep.b()\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert result.conditional == ("if@3",)
        assert [x.canonical for x in result.requirements] == [
            "dep.a", "dep.b"
        ]

def test_collapse_propagates_only_causal_blocker():
    from qps.cipher.foreign.capability_graph import (
        CapabilityDisposition,
        collapse_capability_graph,
    )
    root = CapabilityIdentity("pkg", ("root",))
    good = CapabilityIdentity("pkg", ("good",))
    bad = CapabilityIdentity("pkg", ("bad",))
    graph = build_capability_graph(
        (root,),
        lambda node: {
            root: (good, bad),
            good: (),
            bad: (),
        }[node],
    )
    result = collapse_capability_graph(
        graph,
        lambda node: CapabilityDisposition(
            node,
            "blocked" if node == bad else "proven",
        ),
    )
    assert result.dispositions[good].state == "proven"
    assert result.dispositions[bad].state == "blocked"
    assert result.dispositions[root].state == "blocked"
    assert result.blockers[root] == (bad,)


def test_collapse_blocks_unproven_cycle_without_looping():
    from qps.cipher.foreign.capability_graph import (
        CapabilityDisposition,
        collapse_capability_graph,
    )
    a = CapabilityIdentity("pkg", ("a",))
    b = CapabilityIdentity("pkg", ("b",))
    graph = build_capability_graph(
        (a,),
        lambda node: (b,) if node == a else (a,),
    )
    result = collapse_capability_graph(
        graph,
        lambda node: CapabilityDisposition(node, "proven"),
    )
    assert result.dispositions[a].state == "blocked"
    assert result.dispositions[b].state == "blocked"
    assert not result.ready

def test_parameter_shadowing_does_not_claim_imported_capability():
    assert _ids(
        "import name\n"
        "def run(name):\n"
        "    return name.sub.foo()\n"
    ) == []


def test_assignment_shadowing_stops_later_import_attribution():
    assert _ids(
        "import name\n"
        "first = name.foo()\n"
        "name = local_value\n"
        "second = name.bar()\n"
    ) == ["name.foo"]


def test_function_local_import_does_not_leak_to_sibling_scope():
    assert _ids(
        "def one():\n"
        "    import name\n"
        "    return name.foo()\n"
        "def two():\n"
        "    return name.bar()\n"
    ) == ["name.foo"]


def test_inner_import_shadows_outer_import_only_in_inner_scope():
    assert _ids(
        "import outer as name\n"
        "def run():\n"
        "    import inner as name\n"
        "    return name.foo()\n"
        "value = name.bar()\n"
    ) == ["inner.foo", "outer.bar"]

def test_capability_source_includes_same_module_helper():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(
            "def helper(value):\n"
            "    return value + 1\n"
            "def wanted(value):\n"
            "    return helper(value)\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert [x.canonical for x in result.requirements] == ["pkg.helper"]


def test_capability_source_includes_same_module_global_assignment():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(
            "STATE = object()\n"
            "def wanted():\n"
            "    return STATE\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert [x.canonical for x in result.requirements] == ["pkg.STATE"]


def test_local_variable_does_not_become_module_capability():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(
            "value = 99\n"
            "def wanted():\n"
            "    value = 1\n"
            "    return value\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert result.requirements == ()

def test_selected_function_local_import_is_exact_requirement():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(
            "def wanted(value):\n"
            "    import ext.mod\n"
            "    return ext.mod.foo(value)\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert [x.canonical for x in result.requirements] == ["ext.mod.foo"]


def test_selected_function_import_shadows_module_import():
    import tempfile
    from pathlib import Path
    from qps.cipher.foreign.capability_graph import resolve_python_capability_source

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "pkg.py"
        path.write_text(
            "import outer as name\n"
            "def wanted():\n"
            "    import inner as name\n"
            "    return name.foo()\n"
        )
        result = resolve_python_capability_source(
            CapabilityIdentity("pkg", ("wanted",)),
            path,
        )
        assert result is not None
        assert [x.canonical for x in result.requirements] == ["inner.foo"]

def test_use_before_local_assignment_does_not_resolve_outer_import():
    source = (
        "import name\n"
        "def wanted():\n"
        "    name.foo()\n"
        "    name = object()\n"
    )
    requirements = discover_used_capabilities(source)
    assert [x.identity.canonical for x in requirements] == []


def test_global_declaration_preserves_outer_import_binding():
    source = (
        "import name\n"
        "def wanted():\n"
        "    global name\n"
        "    name.foo()\n"
    )
    requirements = discover_used_capabilities(source)
    assert [x.identity.canonical for x in requirements] == ["name.foo"]


def test_lambda_parameter_shadows_outer_import():
    source = (
        "import name\n"
        "value = (lambda name: name.foo())(object())\n"
    )
    requirements = discover_used_capabilities(source)
    assert [x.identity.canonical for x in requirements] == []


def test_comprehension_target_shadows_outer_import():
    source = (
        "import name\n"
        "value = [name.foo() for name in values]\n"
    )
    requirements = discover_used_capabilities(source)
    assert [x.identity.canonical for x in requirements] == []

def test_constant_getattr_on_bound_namespace_is_exact_capability():
    from qps.cipher.foreign.capability_graph import discover_capability_usage
    result = discover_capability_usage(
        'import name\nvalue = getattr(name, "foo")\n'
    )
    assert [x.identity.canonical for x in result.requirements] == ["name.foo"]
    assert result.blockers == ()


def test_runtime_getattr_on_bound_namespace_blocks():
    from qps.cipher.foreign.capability_graph import discover_capability_usage
    result = discover_capability_usage(
        "import name\nvalue = getattr(name, member)\n"
    )
    assert result.blockers == ("dynamic getattr on bound namespace@2",)


def test_star_import_blocks_capability_narrowing():
    from qps.cipher.foreign.capability_graph import discover_capability_usage
    result = discover_capability_usage("from name import *\nfoo()\n")
    assert result.blockers == ("unbounded star import@1",)


def test_dynamic_dunder_import_blocks_unknown_identity():
    from qps.cipher.foreign.capability_graph import discover_capability_usage
    result = discover_capability_usage("__import__(runtime_name)\n")
    assert result.blockers == ("dynamic import identity@1",)


def test_dynamic_importlib_import_module_blocks_unknown_identity():
    from qps.cipher.foreign.capability_graph import discover_capability_usage
    result = discover_capability_usage(
        "import importlib\nimportlib.import_module(runtime_name)\n"
    )
    assert result.blockers == ("dynamic import identity@2",)

def test_valid_closure_lookup_prunes_expander_work():
    root = CapabilityIdentity("pkg", ("root",))
    child = CapabilityIdentity("pkg", ("child",))
    calls = []

    def expand(identity):
        calls.append(identity)
        return ()

    def closure_lookup(identity):
        if identity == root:
            return (child,)
        if identity == child:
            return ()
        return None

    graph = build_capability_graph(
        (root,),
        expand,
        closure_lookup=closure_lookup,
    )
    assert calls == []
    assert set(graph.nodes) == {root, child}
    assert graph.tiers[0].catalog_hits == 1
    assert graph.tiers[1].catalog_hits == 1


def test_catalog_miss_expands_normally():
    root = CapabilityIdentity("pkg", ("root",))
    child = CapabilityIdentity("pkg", ("child",))
    calls = []

    def expand(identity):
        calls.append(identity)
        return (child,) if identity == root else ()

    graph = build_capability_graph(
        (root,),
        expand,
        closure_lookup=lambda identity: None,
    )
    assert calls == [root, child]
    assert set(graph.nodes) == {root, child}
    assert sum(tier.catalog_hits for tier in graph.tiers) == 0

def test_causal_blockers_report_terminal_leaf_through_intermediate():
    from qps.cipher.foreign.capability_graph import (
        CapabilityDisposition,
        collapse_capability_graph,
    )

    root = CapabilityIdentity("pkg", ("root",))
    middle = CapabilityIdentity("pkg", ("middle",))
    leaf = CapabilityIdentity("missing", ("leaf",))

    graph = build_capability_graph(
        (root,),
        lambda identity: {
            root: (middle,),
            middle: (leaf,),
            leaf: (),
        }[identity],
    )
    result = collapse_capability_graph(
        graph,
        lambda identity: CapabilityDisposition(
            identity,
            "blocked" if identity == leaf else "proven",
        ),
    )
    assert result.blockers[root] == (middle,)
    assert result.causal_blockers(root) == (leaf,)

def test_bare_bound_namespace_argument_blocks_instead_of_widening_module():
    from qps.cipher.foreign.capability_graph import (
        discover_capability_usage,
    )

    result = discover_capability_usage(
        "import name\nconsume(name)\n"
    )
    assert not result.requirements
    assert result.blockers == (
        "bound namespace escapes static capability surface@2",
    )


def test_bare_bound_namespace_assignment_blocks_instead_of_widening_module():
    from qps.cipher.foreign.capability_graph import (
        discover_capability_usage,
    )

    result = discover_capability_usage(
        "import name\nvalue = name\n"
    )
    assert not result.requirements
    assert result.blockers == (
        "bound namespace escapes static capability surface@2",
    )

def test_from_import_exact_object_escape_is_not_namespace_escape():
    result = discover_capability_usage(
        "from name import foo\nconsume(foo)\n"
    )
    assert [x.identity.canonical for x in result.requirements] == [
        "name.foo",
    ]
    assert result.blockers == ()


def test_nested_from_import_exact_object_escape_is_not_namespace_escape():
    result = discover_capability_usage(
        "from name.sub import foo\nconsume(foo)\n"
    )
    assert [x.identity.canonical for x in result.requirements] == [
        "name.sub.foo",
    ]
    assert result.blockers == ()


def test_module_namespace_escape_still_blocks():
    result = discover_capability_usage(
        "import name\nconsume(name)\n"
    )
    assert result.requirements == ()
    assert result.blockers == (
        "bound namespace escapes static capability surface@2",
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
        f"CAPABILITY_GRAPH_TEST_SUMMARY "
        f"tests={len(tests)} failures={len(failures)}"
    )
    raise SystemExit(1 if failures else 0)
