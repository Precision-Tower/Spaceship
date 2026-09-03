# QPS Execution Language Design

This document defines the active design space for QPS general execution blocks and the `testSuite` bootstrap target.

It is a design document, not yet the executable language specification.

`docs/QPS.qps` remains the executable specification and must not be updated merely because syntax is proposed here.

## Goal

Define the minimum coherent QPS execution language required to build a QPS-native testing system called `testSuite`.

The goal is not to imitate another programming language.

The goal is to preserve QPS structural identity while adding executable behavior.

## QPS Language Families

Structural QPS:

    key.
    term:
    item-

General execution:

    { ... }

Calculation:

    {% ... }

Geometry:

    {@ ... }

Model:

    {$ ... }

Causal:

    {! ... }

Plain `{}` is intended to be the general execution/control language.

The specialized block families remain distinct languages or semantic domains.

General execution may eventually invoke, consume, or coordinate specialized blocks.

## Structural Ownership

Strong design preference:

QPS executable behavior should remain owned by normal QPS structure.

Example direction:

    engine.
    startup: {
        ...
    };

Rather than inventing a completely separate top-level programming syntax, a Key or Term should be able to own executable behavior where semantically appropriate.

The exact legal attachment points still need to be defined.

Questions include:

- Can a Key directly own `{}`?
- Can a Term own `{}`?
- Can an Item value be `{}`?
- Can execution blocks nest?
- Can specialized blocks contain execution?
- Can execution blocks contain specialized blocks?

## testSuite

`testSuite` is the canonical name of the QPS-native testing library/system.

Intended eventual responsibilities:

- test discovery
- test registration
- test execution
- assertions
- expected-failure/error assertions
- setup and teardown
- fixtures
- parameterization
- filtering
- fail-fast
- concise reporting
- verbose reporting
- machine-readable reporting
- deterministic execution

Expected CLI direction:

    qps test
    qps test discover
    qps test <path>
    qps test -k <filter>
    qps test --fail-fast
    qps test --verbose

These commands are architectural direction, not yet guaranteed implemented CLI.

## Bootstrap Principle

The QPS execution language should be developed against a real executable target.

The first useful target is a QPS-authored test suite approximately capable of expressing:

    tests.

    truth: -test {
        -assert true;
    };

    math: -test {
        -let x = 2;
        -let y = 3;

        -assert {% x + y } == 5;
    };

    branching: -test {
        -let x = 10;

        -if x > 5 {
            -assert true;
        }
        -else {
            -fail "wrong branch";
        }
    };

This is design-direction syntax only.

Codex must compare it against the lexer, parser, AST, runtime, and existing tests before treating any part of it as canonical.

## Execution Vocabulary Under Consideration

Potential executable forms include:

    -test
    -func
    -let
    -set
    -if
    -elif
    -else
    -for
    -while
    -loop
    -break
    -continue
    -return
    -assert
    -fail
    -raises
    -print
    -pass

Not all of these are necessarily correct.

The implementation should converge on the smallest coherent vocabulary needed by real QPS execution.

## Functions

QPS previously moved away from `def` toward `-func`.

Canonical function syntax is not yet established.

Strong candidate direction:

    math.
    add: -func(a, b) {
        -return {% a + b };
    };

Questions still requiring design:

- Are parameters positional only?
- Are type hints allowed?
- Are defaults allowed?
- How are functions referenced?
- How are functions called?
- Is a function itself a Term value?
- What scope does a function capture?
- What is the return-value model?

## Tests

Strong candidate direction:

    resolver_tests.

    surface_resolution: -test {
        -assert true;
    };

A test should be a first-class executable definition that:

- has a stable identity
- can be discovered
- can be filtered
- can pass
- can fail by assertion
- can error due to runtime failure
- can report source location
- can consume fixtures
- can eventually be parameterized

The exact grammar remains open until compared against the implementation.

## Assertions

Minimum testing primitives likely include:

    -assert <expression>;
    -fail <message>;
    -raises <expected> {
        ...
    }

Important semantic distinction:

- assertion failure = test failure
- unexpected runtime exception/error = test error

The exact syntax must be designed against existing runtime/error architecture.

## Bindings and Scope

Execution requires an explicit scope model.

At minimum, design must distinguish:

- document/structural scope
- execution-block scope
- function-local scope
- test-local scope
- fixture scope
- local bindings

Candidate binding operations:

    -let name = expression;
    -set name = expression;

Questions:

- Is `-let` immutable or only declarative?
- Does `-set` require an existing binding?
- Do nested blocks inherit outer bindings?
- Are Terms/Keys directly addressable as bindings?
- How do `[>...]` structural references enter execution scope?

## Control Flow

The execution language needs a canonical control-flow grammar.

Candidate direction:

    -if condition {
        ...
    }
    -elif condition {
        ...
    }
    -else {
        ...
    }

Candidate loops:

    -for ...
    -while ...
    -loop ...

Exact grammar is unresolved.

Whitespace should preferably remain non-semantic.

Braces and explicit terminators should determine structure.

## Expressions

The design must clearly separate:

- statements
- expressions
- calculations
- structural references
- function calls
- specialized block evaluation

`{% ... }` is the calculation domain and should not automatically become synonymous with every QPS expression.

The relationship between general execution expressions and calculation blocks must be defined carefully.

## Structural References

`SymbolReferenceNode` already provides structural semantic navigation.

Execution should be able to consume structural references such as:

    [>shape.dimensions]

without creating a second incompatible reference system.

Existing reference semantics must remain intact.

## Specialized Block Integration

General execution should eventually be able to coordinate specialized domains.

Example design direction:

    simulation.
    run: {
        -let force = {% mass * acceleration };

        -if force > limit {
            {@
                ...
            }
        }
    };

This does not define the final return/value semantics of specialized blocks.

Those contracts must be designed explicitly.

## Discovery

`testSuite` should support filesystem/module discovery.

Preferred direction:

- discover `.qps` documents under configured test roots
- parse documents normally
- register first-class `-test` definitions
- avoid requiring artificial Python-style filename conventions when semantic discovery is sufficient

Potential command:

    qps test discover

Expected output should identify:

- files
- suites/modules
- test names
- total discovered count

## Runner

The runner should eventually perform:

    discover
        ->
    load/parse
        ->
    register
        ->
    fixture setup
        ->
    execute test
        ->
    capture pass/fail/error
        ->
    teardown
        ->
    report

Test execution must be deterministic unless a test explicitly opts into nondeterministic behavior.

## Reporter

The default reporter should be concise.

Example direction:

    QPS testSuite

    ....F..

    FAIL resolver.workspace_escape

    expected:
        error contains "escapes the workspace root"

    received:
        unresolved path

    tests=7
    passed=6
    failed=1
    errors=0

Verbose mode should expose individual test names and timing.

Machine-readable reporting should eventually support CE-OS tooling.

## Fixtures

The fixture system should borrow useful lifecycle ideas from both `pytest` and `unittest` without cloning either API.

Questions:

- fixture declaration syntax
- dependency injection versus explicit references
- test-local versus suite/module scope
- setup/teardown model
- fixture caching
- deterministic cleanup on failure

Do not implement fixture complexity before basic QPS execution is stable.

## Parameterization

Parameterization is a desired capability.

Candidate conceptual example:

    addition: -test[...] (...) {
        ...
    };

The exact syntax is unresolved.

Do not lock parameterization grammar before functions, expressions, and test declarations are stable.

## Formal Grammar

Codex should produce and maintain an EBNF-style recommended grammar here once the existing implementation inventory is complete.

The grammar must cover at minimum:

- execution blocks
- test declarations
- function declarations
- parameters
- statements
- bindings
- branching
- loops
- returns
- assertions
- expected errors
- calls
- semicolon rules
- block nesting
- specialized-block invocation boundaries

## Implementation Inventory

Codex must inspect and document the current state of:

- lexer/tokens
- parser
- AST
- execution runtime
- function runtime
- control-flow runtime
- calculation runtime
- structural-reference runtime
- tests

For each relevant feature classify it as:

- implemented and tested
- implemented but incompletely tested
- parser-only
- AST-only
- runtime-only
- placeholder
- obsolete/legacy

Do not assume existing code is canonical merely because it exists.

## First Implementation Milestone

The first implementation milestone should be the smallest coherent execution subset that advances toward QPS-authored tests.

Likely minimum capability:

- parse a test declaration
- parse/execute `{}`
- test-local execution context
- `-assert`
- pass/fail result
- simple runner
- simple reporter

Additional constructs such as `-let`, calculations, branching, functions, fixtures, and parameterization should be added in dependency order rather than all at once.

Codex should refine this after implementation inventory.

## Design Rule

`testSuite` is the goal.

Execution syntax exists to make useful QPS programs possible.

Do not add syntax merely because traditional programming languages contain it.

Every new execution construct should justify itself against real QPS use cases.
