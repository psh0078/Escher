# Escher V1 Plan

## Goal

Build a deterministic, extensible resilience simulator on top of SimPy, while keeping engine APIs replaceable.

## Scope (V1)

- Core request-flow simulation for microservice call chains.
- Resilience mechanisms: retry, circuit breaker, connection limiter, load balancer, autoscaler.
- Workload + fault injection support via external config files (JSON/YAML).
- Reproducible outputs with experiment metadata.

## Recommended V1 Boundary

- Start with **request-level modeling** (fast delivery, clean architecture).
- Defer detailed **resource contention** (CPU queue/interference) to V1.1.

## Architecture Principles

- SimPy is a backend implementation, not the project identity.
- All scheduling goes through a single core engine interface.
- Time advances only in engine `run()`.
- No hidden global state.
- Determinism by explicit seeding only (`random.Random(seed)`).

## Repository Layout

```text
Escher/
  core/
  model/
    resources/
    workloads/
    resilience/
  experiments/
    configs/
    runners/
  analysis/
    metrics/
  tests/
```

## Milestones

### Phase 0 - Contracts and Engine Adapter (Day 1-2)

- Define engine-agnostic interfaces in `core/`.
- Implement SimPy-backed engine adapter.
- Add RNG utility for deterministic seeded randomness.

### Phase 1 - Minimal Request Lifecycle (Day 3-4)

- Implement request entity and lifecycle events.
- Model service operation execution and dependency calls.
- Ensure all events are scheduled through core interfaces.

### Phase 2 - Resilience MVP (Day 5-8)

- Retry: bounded attempts, backoff strategies.
- Circuit breaker: closed/open/half-open with rolling error threshold.
- Connection limiter: per-dependency in-flight cap.
- Load balancer: round-robin, random, least-inflight.
- Autoscaler: reactive threshold policy with cooldown.

### Phase 3 - Workload and Fault Injection (Day 9-10)

- Workload generators: constant, step, burst, trace/time-series.
- Fault injectors: instance kill, latency injection, restart/recovery.
- Config-driven experiment descriptions in `experiments/configs/`.

### Phase 4 - Metrics and Runner (Day 11-12)

- Add metrics: latency (p50/p95/p99), throughput, error rate.
- Track breaker state transitions, inflight/queue depth, instance counts.
- Runner writes metadata: seed, config hash, commit hash, outputs.

### Phase 5 - Validation and Hardening (Day 13-14)

- Determinism tests (same seed -> same results).
- Edge tests: zero events, simultaneous timestamps, long horizon.
- Stress test: more than 100k scheduled events.

## Definition of Done (V1)

- End-to-end scenario execution from config file to metrics output.
- Resilience features listed in scope are functional.
- Determinism, edge-case, and stress tests pass.
- Engine boundary is clean enough to replace SimPy later.

## Risks and Mitigations

- **Risk:** Tight coupling to SimPy internals.
  - **Mitigation:** Keep SimPy calls isolated to `core` adapter layer.
- **Risk:** Non-deterministic behavior from implicit randomness.
  - **Mitigation:** Centralized seeded RNG passed through components.
- **Risk:** Over-scoping early (contention modeling too soon).
  - **Mitigation:** Lock request-level V1 scope; schedule contention for V1.1.

## V1.1 (Next)

- Add explicit resource contention models in `model/resources/`.
- Introduce queueing policies and interference effects.
- Calibrate demand/capacity using measured traces when available.
