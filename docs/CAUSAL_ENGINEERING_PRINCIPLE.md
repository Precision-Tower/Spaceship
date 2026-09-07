# CE-OS Causal Engineering Principle

## Purpose

CE-OS exists to model engineered systems from explicit physical relationships rather than from opaque summary values.

The system is intended to preserve enough causal information that a result can be followed backward through the relationships, assumptions, equations, geometry, supplied values, and state that produced it.

The objective is not merely to calculate an answer.

The objective is to understand why that answer exists.

---

## Primary Rule

**Do not replace a physical relationship with a summary metric when the underlying relationship can be represented directly.**

For example, efficiency is not an authoritative primitive of an engineered component.

An efficiency value may be calculated afterward for a particular operating state:

    efficiency = chosen_output / chosen_input

but that value does not explain the behavior of the component.

CE-OS should instead represent the governing quantities themselves.

Examples:

Electrical:

    voltage
    current
    resistance
    electromagnetic state

Rotational mechanical:

    torque
    angular velocity
    angular displacement
    inertia
    mechanical resistance

Hydraulic / fluid:

    pressure
    pressure differential
    volumetric flow
    velocity
    density
    viscosity
    geometry
    fluid resistance

Geometry:

    dimensions
    radii
    areas
    volumes
    clearances
    placement
    connections

Material:

    density
    mass
    mechanical properties
    thermal properties

The relationships between these quantities are the Engineering truth.

Metrics are projections of that truth.

---

## Whitebox Mathematics

Engineering equations should remain inspectable whenever practical.

For example:

    volume {%
        pi * ((outer_radius ^ 2) - (inner_radius ^ 2)) * length
    %}

is preferred over hiding the same relationship behind an opaque helper whose internal reasoning cannot be followed.

Reusable algorithms are appropriate when a sequence of operations genuinely deserves a reusable identity.

Simple equations should remain equations.

The purpose of abstraction is reuse, not concealment.

---

## Multi-Domain Energy Systems

CE-OS must not assume that quantities remain constant merely because energy passes between domains.

Different domains expose different paired variables.

Electrical power:

    P = V * I

Rotational mechanical power:

    P = torque * angular_velocity

Hydraulic power:

    P = pressure_difference * volumetric_flow

The values of force, torque, pressure, flow, voltage, current, and speed may change dramatically across a system.

The important requirement is that CE-OS preserve the relationships responsible for those changes.

A design may intentionally trade:

    torque for speed
    speed for torque
    pressure for flow
    flow for pressure
    voltage for current
    current for voltage

These transformations are not automatically characterized as good or bad by a single efficiency coefficient.

They are operating states that must be evaluated from the complete causal model.

---

## HEV — Hydraulic Electric System

A primary CE-OS engineering target is the Hydraulic Electric System.

The proposed system is a closed rotary energy-conversion loop:

    DC electrical
        ->
    mechanical
        ->
    fluid / hydraulic
        ->
    mechanical
        ->
    AC electrical
        ->
    DC electrical
        ->
    repeat

A physical implementation is conceptually:

    battery
        ->
    DC motor
        ->
    water pump
        ->
    circulating water
        ->
    hydraulic turbine
        ->
    alternator
        ->
    rectification / charging
        ->
    battery

The HEV is not to be accepted as possible or impossible by assumption.

CE-OS is intended to model it causally.

Every component must expose the actual relationships necessary to determine its behavior.

Examples include:

Battery:

    voltage
    current
    state
    charge
    discharge

DC motor:

    voltage
    current
    magnetic field
    back EMF
    torque
    angular velocity

Pump:

    shaft torque
    angular velocity
    geometry
    pressure rise
    volumetric flow

Fluid circuit:

    geometry
    pressure
    flow
    velocity
    density
    viscosity
    resistance
    transient state

Turbine:

    incoming pressure
    outgoing pressure
    flow
    geometry
    torque
    angular velocity

Alternator:

    angular velocity
    shaft torque
    magnetic interaction
    counter-torque
    voltage
    current
    electrical load

The complete system should determine its own operating point from these interacting relationships.

---

## Falsifiability

CE-OS must not be written to prove the HEV works.

CE-OS must not be written to prove the HEV cannot work.

It must be written so that the HEV can fail honestly.

The system should be capable of answering:

    What changed?

    Why did it change?

    What opposed the change?

    What depended upon it?

    What quantity increased?

    What quantity decreased?

    What relationship caused that exchange?

    Where did the resulting state originate?

If the HEV decays, CE-OS should expose the causal path responsible.

If it reaches a steady operating state, CE-OS should expose the relationships that sustain that state.

If the model predicts growth, CE-OS should expose every contributing relationship so the result can be audited for omitted physics, incorrect equations, hidden inputs, or legitimate physical causes.

No conclusion is privileged.

The causal trail is privileged.

---

## Single Engineering Identity

An engineered object should have one semantic identity.

Its different representations should be derived views or consequences of that identity.

For example, a Pipe should not separately exist as:

    CAD Pipe
    Simulation Pipe
    Blueprint Pipe
    Workbench Pipe
    AI Pipe
    Engineering Pipe

Instead:

    Pipe
        |
        +-- geometry
        +-- equations
        +-- material
        +-- mass
        +-- ports
        +-- spatial constraints
        +-- simulation behavior
        +-- construction information
        +-- Agency context

Workbench may own UI state.

It must not own authoritative Engineering state.

Simulation evaluates the engineered object.

It does not create an independent authoritative copy of it.

Blueprints describe the engineered object.

They do not become a second source of dimensions.

Agency reasons over the engineered object and its causal graph.

It does not need a separately reconstructed representation.

---

## QPS

Quick Parse Standard is the computing language used to express CE-OS semantics.

QPS is intended to combine:

    explicit recursive structure
    executable behavior
    engineering knowledge
    mathematical relationships
    causal relationships
    filesystem-extended semantic organization

without requiring whitespace to carry syntax.

The filesystem can extend the parseable semantic structure through `_index.qps` files and nested QPS definitions.

This allows physical organization, semantic organization, ownership, and discovery to reinforce one another.

---

## Derived State

Whenever possible, CE-OS should store meaningful relationships and derive consequences.

Examples:

    dimensions
        ->
    geometry

    geometry + density
        ->
    mass

    connections
        ->
    placement

    pressure + flow + geometry
        ->
    hydraulic state

    torque + angular velocity
        ->
    mechanical state

Derived state should remain traceable to the definitions and supplied values that produced it.

---

## Engineering Standard

When implementing a CE-OS capability, ask:

1. What are the real physical quantities?
2. What relationships connect them?
3. Which quantities are supplied?
4. Which quantities are derived?
5. What assumptions are being made?
6. What state changes with time?
7. What depends upon this result?
8. Can the result be traced back to its causes?
9. Are we storing an authoritative fact or merely a convenient projection?
10. Have we hidden physical behavior behind a summary value?

If the causal relationships can be represented directly, represent them directly.

---

## Core Principle

**CE-OS does not exist to tell us what to believe about an engineered system.**

**CE-OS exists to preserve enough of the engineered system that its consequences can be calculated, inspected, challenged, simulated, and traced back to their causes.**

The model does not win.

The hypothesis does not win.

The causal trail wins.
