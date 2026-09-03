# Pipe Semantic Contract

## Status

Architecture contract for migration of CE-OS pipe, fitting, port, connection,
and routing semantics into Engineering/QPS.

This contract does not establish physical validation, pressure rating,
manufacturability, leak integrity, or build readiness.

## Authority

Engineering owns:

- pipe and fitting meaning
- dimensional resolution
- material assignment
- port topology
- connection topology
- compatibility evaluation
- placement resolution
- routing semantics
- calculated mass and volume
- unresolved variables
- blocked/prohibited interpretations
- geometry requests
- rebuild dependency resolution

QPS is the authored semantic representation.

Engineering C++ executes geometry requests.

OCCT owns native B-rep construction and native geometry operations.

Workbench owns:

- operator gestures
- dialogs and controls
- selection
- transient ghosts
- candidate visualization
- display meshes
- explicit candidate-intent submission

Workbench does not establish Engineering truth.

## Pipe Definition

A Pipe Definition describes a reusable engineering article.

It may contain:

- family
- nominal size
- schedule
- material
- outside diameter
- inside diameter
- wall thickness
- interface topology

Catalog values may resolve authored nominal values into physical dimensions.

A definition does not contain world placement.

## Pipe Instance

A Pipe Instance references a Pipe Definition and supplies instance state.

Instance state includes:

- object identity
- length
- placement
- run membership
- fill state
- resolved dimensions
- ports
- connections
- calculated quantities
- geometry state
- diagnostics

Changing a Pipe Instance parameter requires Engineering resolution.

Moving a Godot node does not change authoritative Pipe Instance placement.

## Pipe Dimensions

The canonical dimensional relationship is:

    outside diameter
    inside diameter
    wall thickness

Radius values may be derived for calculation or geometry execution.

Nominal size and schedule are specification identifiers and must not be
silently treated as measured physical diameter.

Catalog resolution must remain explicit.

## Fitting Definition

A Fitting Definition describes a reusable pipe-interface article.

Examples include:

- coupling
- 90 degree elbow

A fitting definition may contain:

- fitting type
- standard
- nominal size
- schedule
- material
- dimensional rules
- interface topology
- takeoff rules

## Fitting Instance

A Fitting Instance references a Fitting Definition.

Instance state may include:

- object identity
- placement
- roll
- resolved dimensions
- resolved takeoff
- ports
- connections
- geometry state
- diagnostics

Roll is an instance parameter around a constrained connection axis.

Visual alignment does not establish a valid physical joint.

## Ports

Ports are Engineering interfaces.

A port has semantic identity independent of its rendered marker.

A port may contain:

- port id
- interface type
- dimensional compatibility data
- local transform
- resolved world transform
- state
- connection reference
- diagnostics

Definitions establish port topology and local interface rules.

Instances resolve port transforms into Engineering space.

Godot port markers are disposable representations of these interfaces.

## Connections

Connections are first-class Engineering relationships.

A connection identifies two endpoints:

    object A / port A
    object B / port B

Connection state must not be inferred solely from spatial coincidence.

Compatibility evaluation belongs to Engineering.

Compatibility may consider:

- interface type
- dimensions
- specification
- material/system constraints
- connection state
- additional Engineering rules

Exact floating-point equality is not a canonical compatibility rule.

A connection record does not prove:

- leak integrity
- pressure safety
- manufacturability
- physical assembly
- build readiness

## Placement

Placement is Engineering instance state.

Workbench may create transient candidate placement.

Engineering resolves accepted candidate placement.

Renderer-specific axis conventions are not Engineering semantics.

In particular, Godot cylinder orientation conventions must not become part of
the canonical Pipe definition.

## Routing

Routing creates or modifies Engineering instances and relationships.

A route may resolve:

- endpoints
- pipe length
- pipe placement
- fitting requirements
- fitting placement
- connection topology
- affected run members

Routing calculations belong to Engineering.

Workbench may author routing intent but does not resolve authoritative routes.

## Runs

A run is an Engineering relationship/grouping between compatible pipe-system
instances.

Run-wide parameter changes are Engineering operations.

Workbench must not establish authoritative run membership by walking Godot
nodes.

A request such as changing run outside diameter is submitted as intent.
Engineering determines affected instances and rebuild dependencies.

## Trim and Extend

Trim and extend are Engineering operations.

Workbench may supply:

- target object
- target endpoint
- requested amount or target
- operator context

Engineering resolves:

- resulting length
- resulting placement
- port transforms
- connection effects
- routing effects
- geometry rebuild
- diagnostics

Workbench must not make the resulting geometry authoritative by directly
mutating a rendered node.

## Calculated Quantities

Engineering may derive:

- material volume
- contained volume
- mass
- buoyancy contribution
- centerline length
- fitting takeoff

Calculated quantities retain their evidence state.

Successful calculation does not imply physical validation.

## Geometry

Pipe and fitting semantics are not render primitives.

Engineering resolves semantic instances into geometry actions.

Target flow:

    QPS authored state
        -> Engineering resolution
        -> geometry actions
        -> Engineering C++
        -> OCCT B-rep
        -> triangulation/display contract
        -> Workbench Godot rendering

A pipe may use cylindrical/native hollow geometry internally.

An elbow may use sweep/torus-like native geometry internally.

Those implementation primitives do not define the Engineering article.

The current Godot pipe and elbow meshes are compatibility visualization only.

## Candidate Intent

Workbench produces explicit candidate intent.

Candidate intent may request:

- create pipe
- create fitting
- connect
- disconnect
- move
- trim
- extend
- change dimension
- change run parameter
- delete

Candidate intent is not Engineering state.

Engineering may:

- accept
- reject
- modify
- leave unresolved

The result returned to Workbench is an Engineering projection suitable for
inspection and rendering.

## Migration Sources

The existing Python pipe implementation is behavioral reference material for:

- catalog resolution
- hollow-cylinder accounting
- fittings
- ports
- connections
- placement
- routing

Existing Workbench Ghost Pipe behavior is reference material for operator
interaction and for identifying Engineering semantics that leaked into Godot.

Neither implementation is automatically canonical merely because it exists.

## Prohibited Interpretations

The following interpretations are prohibited:

- rendered pipe equals Engineering pipe
- ghost pipe equals Engineering pipe
- visual alignment equals physical connection
- connection record equals leak-free connection
- fitting geometry equals pressure-rated fitting
- calculated candidate equals build-ready component
- successful native geometry equals manufacturability
- packet loading equals validation
- simulation playback equals validation
- Godot mesh equals authoritative CAD

## Migration Rule

For each existing Pipe behavior:

- Godot interaction/display behavior remains in Workbench
- authored Engineering meaning moves to QPS
- semantic calculation/resolution belongs to Engineering
- native CAD construction belongs to Engineering C++/OCCT
- existing Python remains reference or transitional execution until its
  replacement is proven

Migration must preserve known-good behavior until the replacement path is
tested.
