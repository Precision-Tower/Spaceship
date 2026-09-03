# Workbench Migration Checklist

## Purpose

Migrate CE-OS Workbench from the prototype architecture that established
Godot interaction and Python Engineering behavior into the intended
whitebox architecture:

    Operator
        -> Workbench intent
        -> Engineering / QPS semantics
        -> Engineering resolution
        -> C++ geometry
        -> OCCT native geometry
        -> display projection
        -> Workbench

Workbench exposes Engineering spatially and interactively without becoming
Engineering truth.

This checklist is the Workbench migration mission record.

## Migration States

Each migration surface is classified as:

- **PRESERVE** — proven behavior or knowledge that must survive migration.
- **MIGRATE** — semantic ownership moves to its canonical layer.
- **REPLACE** — transitional implementation is superseded by the new boundary.
- **VALIDATE** — intended behavior requires implementation/runtime proof.
- **RETIRE** — compatibility code may be removed only after replacement proof.

Do not retire known-good behavior before its replacement is demonstrated.

---

# 1. Authority Boundary

## Workbench / Godot

### PRESERVE

- [ ] Operator interaction.
- [ ] Viewport navigation.
- [ ] Selection and highlighting.
- [ ] Object tree presentation.
- [ ] Inspector presentation.
- [ ] Dialogs and immediate UI input validation.
- [ ] Ghost authoring UX.
- [ ] Transient candidate visualization.
- [ ] Port markers and selection affordances.
- [ ] Simulation playback visualization.
- [ ] Explicit candidate-intent submission.

### MIGRATE

- [ ] Remove Engineering semantic authority from GDScript.
- [ ] Treat Workbench session/object dictionaries as UI projections/caches.
- [ ] Treat Godot nodes and meshes as disposable representations.
- [ ] Convert Engineering-backed edits into explicit intent requests.

### VALIDATE

- [ ] Workbench can display Engineering-resolved objects without redefining them.
- [ ] Selection maps rendered geometry back to stable Engineering identity.
- [ ] Inspector state distinguishes authored, resolved, unresolved, and diagnostic data.
- [ ] Rejected Engineering intent remains visible to the operator.

## Engineering / QPS

### MIGRATE

- [ ] Authored Engineering meaning into QPS.
- [ ] Design Definition semantics into QPS.
- [ ] Design Instance semantics into Engineering/QPS.
- [ ] Parameter resolution into Engineering.
- [ ] Port/interface semantics into Engineering/QPS.
- [ ] Relationship/topology semantics into Engineering/QPS.
- [ ] Rebuild dependency resolution into Engineering.
- [ ] Diagnostics and unresolved state into Engineering.

### VALIDATE

- [ ] QPS meaning remains independent of Workbench representation.
- [ ] Engineering can accept, reject, modify, or leave Workbench intent unresolved.
- [ ] Engineering outputs contain sufficient semantic identity for Workbench inspection.

## Engineering C++ / OCCT

### PRESERVE

- [ ] Native geometry execution boundary.
- [ ] OCCT B-rep construction.
- [ ] Native geometry validity checks.
- [ ] Triangulation/display extraction.

### VALIDATE

- [ ] QPS-authored state reaches native geometry through Engineering actions.
- [ ] Semantic object identity survives native geometry generation.
- [ ] Workbench receives disposable render geometry tied to Engineering identity.
- [ ] Successful geometry generation is not represented as physical validation.

## Python

### PRESERVE

- [ ] Existing Python Engineering behavior as migration/reference evidence.
- [ ] Proven calculations and catalog knowledge until replacement is demonstrated.
- [ ] Existing project generators required by known-good workflows during transition.

### RETIRE

- [ ] Retire Python authority only after equivalent or intentionally changed
      QPS/Engineering behavior is tested.
- [ ] Do not perform line-by-line Python-to-QPS translation merely to remove Python.

---

# 2. Workbench State Model

## Current Findings

Workbench currently contains overlapping state surfaces including:

- WorkbenchSession.
- WorkbenchProject.
- WorkbenchObject.
- WorkbenchRegistry.
- project object dictionaries.
- packet-derived object dictionaries.
- transient ghost state.
- Godot display nodes.

`WorkbenchSession` is to be treated as a Workbench-side projection/cache and
transient interaction surface, not Engineering truth.

### MIGRATE

- [ ] Separate Engineering projection state from transient authoring state.
- [ ] Separate selection state from Engineering object state.
- [ ] Separate display-node lifecycle from semantic-object lifecycle.
- [ ] Remove direct Engineering-looking mutation from UI state where it is
      currently treated as authoritative.

### VALIDATE

- [ ] Reloading an Engineering projection reconstructs Workbench state.
- [ ] Destroying/recreating a display node does not destroy Engineering identity.
- [ ] UI selection does not mutate Engineering meaning.
- [ ] Transient ghost state cannot be mistaken for resolved Engineering state.

---

# 3. Packet and Data Boundary

### PRESERVE

- [ ] Packet lineage.
- [ ] Object identity.
- [ ] unresolved variables.
- [ ] blocked/prohibited interpretations.
- [ ] packet links.
- [ ] evidence-state distinctions.

### MIGRATE

- [ ] Treat packets/projections as transport and inspection contracts, not truth.
- [ ] Candidate intent becomes an explicit Workbench -> Engineering boundary.
- [ ] Engineering result becomes the authoritative source for resolved UI projection.

### VALIDATE

- [ ] Packet loading does not imply validation.
- [ ] Unknown fields remain visible/preserved where practical.
- [ ] Missing optional display data does not silently create Engineering facts.
- [ ] Candidate intent and resolved state are distinguishable in the UI.

### RETIRE

- [ ] Legacy packet routes only after their replacement path is proven.
- [ ] Float-specific compatibility coupling only after equivalent current routing exists.

---

# 4. Semantic Leakage from Workbench

The following Engineering behavior has been observed in GDScript and must not
remain authoritative there.

### MIGRATE

- [ ] Pipe dimensional semantics.
- [ ] Pipe direction/placement semantics.
- [ ] Pipe port transforms as Engineering truth.
- [ ] Material inheritance.
- [ ] OD inheritance.
- [ ] Run membership semantics.
- [ ] Run-wide parameter propagation.
- [ ] Connected-pipe realignment.
- [ ] Trim/extend consequences.
- [ ] Fitting attachment semantics.
- [ ] Fitting dimensional inheritance.
- [ ] Fitting roll semantics beyond operator input.
- [ ] Engineering rebuild propagation.
- [ ] Connection compatibility.
- [ ] Routing consequences.

### PRESERVE IN GODOT

- [ ] Mouse ray projection.
- [ ] Viewport plane/axis interaction.
- [ ] Keyboard constraints.
- [ ] Popup menus.
- [ ] dialogs.
- [ ] transient movement/rotation previews.
- [ ] visual highlighting.
- [ ] candidate transparency/material.
- [ ] selection/raycast collision.
- [ ] camera-dependent placement UX.

---

# 5. Native Geometry Migration

## Target Flow

    QPS authored state
        -> Engineering resolution
        -> geometry actions
        -> Engineering C++
        -> OCCT B-rep
        -> triangulation/display contract
        -> Workbench renderer

### MIGRATE

- [ ] Authoritative primitive dimensions out of Godot rendering code.
- [ ] Authoritative pipe geometry out of Godot.
- [ ] Authoritative fitting geometry out of Godot.
- [ ] Engineering geometry requests through the existing C++ geometry boundary.

### PRESERVE

- [ ] Workbench material/display styling.
- [ ] selection collision representations.
- [ ] transient preview geometry where explicitly non-authoritative.
- [ ] compatibility rendering during migration.

### VALIDATE

- [ ] Native geometry identity maps back to Engineering semantic identity.
- [ ] Geometry failure remains visible.
- [ ] Last known-good geometry is not silently replaced by invalid output.
- [ ] Render mesh can be discarded and regenerated.
- [ ] Workbench does not reconstruct authoritative CAD from a render mesh.

### RETIRE

- [ ] Godot authoritative procedural pipe geometry.
- [ ] Godot authoritative `pipe_elbow_90` geometry.
- [ ] geometry fallbacks only when equivalent native-display path is proven.

---

# 6. QPS Instance UX

### MIGRATE

- [ ] Discover authored QPS Items.
- [ ] Discover unresolved parameters.
- [ ] Distinguish supplied values from derived values.
- [ ] Represent explicit parameter binding.
- [ ] Represent Design Definition separately from Design Instance.
- [ ] Workbench edits instances without silently modifying reusable definitions.

### VALIDATE

- [ ] unresolved values remain visible.
- [ ] blocked state remains visible.
- [ ] derived values identify their Engineering source.
- [ ] UI controls are representations, not authoritative values.
- [ ] Engineering rejection/modification is surfaced after an edit request.

---

# 7. Ports, Connections, and Assemblies

### MIGRATE

- [ ] Ports become Engineering interfaces with stable semantic identity.
- [ ] Port world transforms are resolved from Engineering instance state.
- [ ] Connections become first-class Engineering relationships.
- [ ] Assembly topology is independent of Godot scene hierarchy.
- [ ] Spatial graph and functional graph remain distinct.
- [ ] Connection compatibility belongs to Engineering.

### VALIDATE

- [ ] Port marker selection resolves the correct Engineering interface.
- [ ] Spatial coincidence does not automatically create a connection.
- [ ] Connection records do not imply leak integrity or pressure safety.
- [ ] Assembly display survives scene-node recreation.

---

# 8. Simulation and Evidence

### PRESERVE

- [ ] Playback.
- [ ] visualization.
- [ ] measurement presentation.
- [ ] operator inspection.

### MIGRATE

- [ ] Simulation state consumed as Engineering output rather than UI truth.

### VALIDATE

- [ ] Playback does not establish correctness.
- [ ] Visualization does not promote evidence.
- [ ] Engineering diagnostics remain visible during playback.
- [ ] Physical validation remains distinct from software execution success.

---

# 9. Vertical Migration Specimen — Pipe

Pipe is the first full-stack migration specimen.

Canonical architecture contract:

    Engineering/qps/docs/PIPE_SEMANTIC_CONTRACT.md

## Preserve

- [ ] Ghost placement UX.
- [ ] Port selection.
- [ ] Pipe dialogs.
- [ ] Candidate visualization.
- [ ] Python catalog dimensional knowledge.
- [ ] Hollow-cylinder accounting knowledge.
- [ ] Fitting/takeoff knowledge.
- [ ] Routing behavior.
- [ ] Connection evidence distinctions.

## Migrate — Pipe

- [ ] Pipe Definition -> Engineering/QPS.
- [ ] Pipe Instance -> Engineering/QPS.
- [ ] nominal size and schedule resolution -> Engineering/QPS.
- [ ] outside/inside diameter and wall thickness -> resolved Engineering state.
- [ ] material -> Engineering/QPS.
- [ ] length -> Engineering instance.
- [ ] placement -> Engineering instance.
- [ ] fill state -> Engineering instance.
- [ ] calculated mass/volume -> Engineering.

## Migrate — Ports

- [ ] Port A/B topology -> Engineering/QPS.
- [ ] local port transform -> Engineering.
- [ ] world port transform -> resolved Engineering state.
- [ ] port state -> Engineering.
- [ ] connection reference -> Engineering.

## Migrate — Connections

- [ ] Connections -> first-class Engineering relationships.
- [ ] compatibility -> Engineering.
- [ ] replace exact floating-point dimensional equality as canonical compatibility.
- [ ] preserve prohibited interpretations for unvalidated joints.

## Migrate — Pipe Runs

- [ ] Run membership -> Engineering/QPS.
- [ ] run-wide dimensional policy -> Engineering.
- [ ] affected-member resolution -> Engineering.
- [ ] rebuild dependency propagation -> Engineering.

## Migrate — Fittings

- [ ] Fitting Definition -> Engineering/QPS.
- [ ] Coupling -> Engineering/QPS.
- [ ] Elbow90 -> Engineering/QPS.
- [ ] fitting standard -> Engineering/QPS.
- [ ] fitting takeoff -> Engineering calculation.
- [ ] fitting roll -> instance intent/resolved state.
- [ ] fitting ports -> Engineering interfaces.

## Migrate — Operations

- [ ] create pipe.
- [ ] create fitting.
- [ ] connect ports.
- [ ] disconnect ports.
- [ ] trim pipe.
- [ ] extend pipe.
- [ ] change pipe parameter.
- [ ] change run parameter.
- [ ] route pipe between ports.
- [ ] delete Engineering object.

## Replace

- [ ] Direct Workbench mutation as Engineering truth.
- [ ] Workbench-side pipe rebuild propagation.
- [ ] Workbench-side run traversal for authoritative changes.
- [ ] Workbench-side connected-pipe realignment as authority.
- [ ] Godot cylinder-axis conventions embedded in Engineering semantics.
- [ ] Godot elbow-mesh orientation embedded in Engineering semantics.

## Validate — First Vertical Slice

- [ ] Author a QPS Pipe definition.
- [ ] Resolve one Pipe instance.
- [ ] Resolve outside diameter.
- [ ] Resolve inside diameter.
- [ ] Resolve wall thickness.
- [ ] Resolve length.
- [ ] Resolve placement.
- [ ] Resolve Port A/B.
- [ ] Emit Engineering geometry action.
- [ ] Construct native hollow pipe with OCCT.
- [ ] Validate native B-rep.
- [ ] Triangulate native shape.
- [ ] Preserve semantic object ID.
- [ ] Display result in Workbench.
- [ ] Select displayed pipe and recover Engineering identity.
- [ ] Inspect resolved parameters.
- [ ] Keep render mesh disposable.

## Validate — Intent Round Trip

- [ ] Workbench creates transient pipe candidate.
- [ ] Workbench submits explicit candidate intent.
- [ ] Engineering resolves or rejects intent.
- [ ] Workbench replaces/updates candidate representation from Engineering result.
- [ ] Rejected/unresolved state remains visible.

## Retire

Only after replacement proof:

- [ ] Python Pipe authority.
- [ ] Python fitting authority.
- [ ] Python connection authority.
- [ ] Python routing authority.
- [ ] `ghost_pipe_fallback`.
- [ ] `ghost_fitting_fallback`.
- [ ] duplicated GDScript Engineering semantics.
- [ ] old Float-specific packet-generation coupling.

---

# 10. Future Migration Specimens

After Pipe establishes the complete architecture:

- [ ] Port.
- [ ] Connection.
- [ ] PipeRun.
- [ ] Coupling.
- [ ] Elbow90.
- [ ] generic primitive instantiation.
- [ ] feature inspection.
- [ ] assemblies.
- [ ] measurement.
- [ ] manufacturing-oriented workflows.

Do not expand migration breadth until the first vertical slice proves the
authority boundary end-to-end.

---

# 11. Legacy Retirement Rules

- [ ] Never remove a known-good path solely because a new path exists.
- [ ] Prove replacement behavior first.
- [ ] Record intentional behavioral differences.
- [ ] Preserve evidence/prohibited-interpretation semantics.
- [ ] Preserve operator capability during migration.
- [ ] Keep compatibility rendering explicitly non-authoritative.
- [ ] Avoid unrelated cleanup while migration work is active.
- [ ] Use path-limited staging.
- [ ] Do not use `git add .`.
- [ ] Preserve unrelated Workbench WIP.

---

# 12. Workbench Migration Exit Criteria

Migration is complete when:

- [ ] Workbench does not own Engineering truth.
- [ ] Workbench emits explicit operator intent.
- [ ] QPS expresses authored Engineering semantics.
- [ ] Engineering resolves parameters and relationships.
- [ ] Engineering owns rebuild consequences.
- [ ] C++/OCCT owns authoritative native CAD construction.
- [ ] Godot consumes disposable geometry/display projections.
- [ ] semantic identity survives QPS -> Engineering -> OCCT -> Workbench.
- [ ] unresolved and failed states remain visible.
- [ ] visualization is never silently promoted to validation.
- [ ] Python compatibility paths required by this migration have either been
      deliberately retained or retired with replacement proof.
- [ ] legacy GDScript Engineering semantics have been retired with replacement proof.
- [ ] Pipe has passed the complete vertical-slice validation.
