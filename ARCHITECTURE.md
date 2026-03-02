# Escher Architecture (V1 Contract)

## Purpose

This document defines the V1 architecture contract for Escher to preserve modularity, determinism, and backend replaceability.

## Layer Boundaries

- `core/`
  - Owns simulation time, scheduling, and engine adapters.
  - Exposes a single scheduling interface (`Engine`).
  - Must not contain resilience or experiment-specific behavior.

- `model/`
  - Owns workload semantics, resource/dependency behavior, and resilience mechanisms.
  - Uses `core.Engine` only for scheduling/time interaction.
  - Must not import experiment runners.

- `experiments/`
  - Owns config parsing, scenario assembly, metadata logging, and run orchestration.
  - Must externalize parameters in JSON/YAML.

- `analysis/`
  - Owns post-run metrics and plotting.
  - Read-only with respect to simulation state.

## Request Lifecycle Contract

The canonical request flow for V1 is:

1. arrival
2. admission (`connection_limiter`)
3. route selection (`load_balancer`)
4. pre-call guard (`circuit_breaker.allow_request`)
5. dependency/service call
6. outcome record (`circuit_breaker.record`)
7. retry decision (`retry` policy)
8. completion + metrics write

Resilience hooks are model-layer concerns and must never be moved into `core`.

## Determinism Contract

- All randomness must use explicitly seeded `random.Random(seed)` instances.
- A run is reproducible if identical `{config, seed, version}` yields identical outputs.
- Time advances only through `engine.run(...)`.

## Performance Notes

- Scheduling path target complexity: `O(log n)` per event with heap-based backends.
- Circuit breaker rolling window trim is amortized `O(1)` per record with deque pop-left.
- Avoid repeated object allocations inside high-frequency callbacks where possible.

## Canonical Experiment Config Shape (V1)

```json
{
  "simulation_metadata": {
    "name": "string",
    "duration": 120.0,
    "seed": 42
  },
  "services": [],
  "workloads": [],
  "faultloads": [],
  "policies": {}
}
```

V1 execution may start with a reduced subset, but all new experiment features should converge to this shape.

## Run Artifact Contract

Each experiment run should emit:

- `seed`
- `config_hash`
- `git_commit_hash`
- key metrics (latency percentiles, throughput, error/success rates)
