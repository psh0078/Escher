# AGENTS.md

## Project goal (high-level)

We are building a production-grade discrete-event simulator whose *capabilities* are comparable to MiSim for resilience evaluation (fault injection, recovery policies, retries/replication/failover, etc.).

Non-goals:
- Do not replicate MiSim’s codebase or match its API 1:1.
- Do not introduce architecture that binds us to one engine (SimPy is a modeling layer, not the identity of the project).

Our differentiators:
- Better modularity + extensibility
- Option for a high-performance engine backend
- More explicit low-level performance modeling (contention, queues, resource interference)

You may read MiSim paper located in the project root directory.

## Purpose

This repository supports the development of **COSIMO**, a production-grade, extensible discrete-event simulator for resilience-aware and performance-aware system modeling.

AI agents (Codex, GPT-based tools, etc.) may assist in:

* Writing modular simulator components
* Implementing experiments
* Refactoring for clarity and performance
* Generating test scaffolding
* Improving documentation

Agents must follow the architectural and engineering principles defined below.

---

# Core Philosophy

1. **Architecture first, implementation second**

   * Do not introduce shortcuts that break modularity.
   * Engine and modeling layers must remain separable.

2. **Determinism over cleverness**

   * Simulation runs must be reproducible.
   * No hidden randomness without explicit seeding.

3. **Explicit over implicit**

   * No global state unless justified.
   * Avoid magic behavior or hidden coupling.

4. **Scalability awareness**

   * Code should not assume small experiments.
   * Avoid O(n²) structures in core event paths.

5. **Replaceability of the simulation engine**

   * SimPy (or any engine) is a backend.
   * Design APIs so that the engine can be swapped.

---

# Repository Structure

Agents must respect this structure:

```
/core
    event_queue.py
    engine.py
    clock.py

/model
    resources/
    workloads/
    resilience/

/experiments
    configs/
    runners/

/analysis
    metrics/
    plotting/

/tests
```

Rules:

* Core engine code must not depend on experiment code.
* Model layer must not import experiment scripts.
* Analysis must not mutate simulation state.

---

# Coding Standards

### General

* Python 3.11+
* Type hints required
* No wildcard imports
* Avoid side effects in constructors

### Event System

* All scheduled events must go through a single scheduling interface.
* No direct manipulation of the event queue outside the engine.
* Time must advance only inside `run()`.

### Randomness

All randomness must:

```python
rng = random.Random(seed)
```

Never use:

```python
random.random()
```

---

# Performance Rules

Agents must:

* Avoid repeated heap allocations inside tight loops.
* Avoid unnecessary object creation in event callbacks.
* Minimize lambda usage in core scheduling paths.
* Prefer dataclasses for event structures.

If modifying core scheduling logic:

* Provide time complexity analysis in comments.
* Explain trade-offs clearly.

---

# Resilience Modeling Rules

When implementing resilience mechanisms (e.g., retries, replication, failover):

* Failure injection must be configurable.
* Recovery policies must be modular.
* No resilience logic inside the engine layer.
* Resilience belongs to the modeling layer.

---

# Experimentation Protocol

When creating experiment scripts:

1. Configuration must be externalized (YAML or JSON).
2. Experiments must log:

   * seed
   * configuration hash
   * git commit hash
3. Output must be reproducible.

Never hardcode experimental parameters inside runner scripts.

---

# Testing Requirements

For any non-trivial change:

* Unit tests required.
* Determinism test required.
* Edge case tests for:

  * zero events
  * simultaneous timestamps
  * long simulation horizons

Core engine changes must include:

* Stress test with >100k scheduled events.

---

# Documentation Rules

All new modules must include:

* High-level description
* Time complexity notes
* Clear separation of concerns

If changing architecture:

* Update `ARCHITECTURE.md`

---

# What Agents Must NOT Do

* Introduce hidden global state.
* Mix modeling logic with engine logic.
* Add external dependencies without justification.
* Refactor core components without explaining impact.
* Optimize prematurely without profiling justification.

---

# When Refactoring

Agents must provide:

1. Before/after explanation
2. Performance implications
3. Risk analysis
4. Backward compatibility assessment

---

# Long-Term Direction

COSIMO aims to:

* Surpass MiSim-style resilience simulation
* Incorporate low-level performance modeling
* Support large-scale experimental runs
* Enable pluggable high-performance simulation backends

All contributions should move toward:

* Engine modularity
* Performance scalability
* Reproducible experimentation
* Research-grade correctness

---

# Final Rule

If uncertain:

* Preserve modularity.
* Preserve determinism.
* Preserve replaceability.

Architecture stability > short-term convenience.

---

# Session Handoff Rule

At the start of every new session, agents must read the latest handoff log before doing implementation work:

- `HANDOFF_LOG.md`

Agents should use this log to recover prior context, current checkpoint state, and ordered next steps.

___

Most importantly, whenever we implement something, I want to test it out and
see its legit validiy with my own eyes. For pedagogical reason, I want to stop
at each checkpoint and make sure I understand the code and implementation.
