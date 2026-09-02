# Boat Assembly

## Current Milestone

Boat assembly is now the active engineering object inside the Float environment.

Working runtime spine:

```text
Hull/hull_inventory.py
        ↓
Hull/hull_inventory_packet.json
        ↓
boat_assembly.py
        ↓
boat_assembly_packet.json
        ↓
UI/projects/Float/FloatProject.gd
        ↓
Workbench

Confirmed runtime output:

[Workbench] project=float
[Float] assembly=boat_assembly_001 objects=17 packet=boat_assembly_packet

This confirms the Engineering → UI packet bridge is functioning.

This does not validate stability, payload safety, seaworthiness, real-world performance, or physical correctness.

Authority Split

Float owns the environment.

Float is responsible for:

fluid environment
gravity
surface plane
buoyant atmosphere
object-in-fluid behavior
environment-level trials

Boat owns the assembly inside Float.

Boat is responsible for:

hull structure
object placement
assembly hierarchy
mass placement
displacement contribution
equilibrium candidates
unresolved variables
blocked interpretations

Boat does not own the environment.

Boat exists inside Float.

Assembly Progression
Hull
  ↓
Sub-Floor
  ↓
Deck
  ↓
Motor

Each layer builds on the layer below it.

Active Layer: Hull

Current status:

active

Files:

Hull/
├─ hull_inventory.py
└─ hull_inventory_packet.json

Purpose:

define flotation objects
define connector objects
assign object positions
assign assembly groups
calculate mass and displacement summaries
preserve unresolveds and blocked interpretations
Active Integration: Boat Assembly

Files:

boat_assembly.py
boat_assembly_packet.json

Purpose:

consume hull inventory packet
preserve source packet lineage
build boat assembly hierarchy
aggregate objects
calculate assembly summary
expose packet to UI / Workbench
Planned Layers
Sub-Floor/
Deck/
Motor/

These are planned assembly layers.

They should eventually produce their own inventory packets before being merged into boat_assembly_packet.json.

Contract Direction

The active packet shape is assembly-first:

packet_type:
created_at:
evidence_state:
environment:
source_packets:
assembly:
  assembly_id:
  assembly_type:
  hierarchy:
  objects:
  summary:
  unresolved_variables:
  blocked_interpretations:
prohibited_interpretations:

Workbench currently consumes:

assembly.objects
object.render
object.packet_links
Prohibited Interpretations
packet equals validation
visualization equals evidence
positive float margin equals stability
calculated candidate equals safe payload
successful Workbench load equals correct engineering
clean assembly hierarchy equals physical readiness
Current Position
Float
└─ Boat
   ├─ Hull        active
   ├─ Sub-Floor   planned
   ├─ Deck        planned
   └─ Motor       planned

Next intended work:

lock contracts
then build Sub-Floor layer