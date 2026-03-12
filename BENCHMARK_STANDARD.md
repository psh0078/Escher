# Escher Benchmark Standard

This document defines Escher-native quality and performance standards.
MiSim is used as an external reference baseline, not as a design target.

## Goals

- Evaluate Escher on correctness, determinism, scalability, and resilience behavior.
- Keep benchmarks reproducible and configurable via external JSON files.
- Allow side-by-side comparison with MiSim outputs when available.

## Benchmark Pillars

1. Correctness
   - Invariants: completed >= failed, no negative latencies, stable CSV headers.
   - Edge cases: zero events, simultaneous timestamps, long horizons.

2. Determinism
   - Fixed seed runs produce identical request counts and latency traces.
   - Determinism checks should use identical configs and deterministic RNG streams.

3. Scalability
   - Track wall-clock runtime and request throughput.
   - Minimum scale checkpoints: around 10k, 100k, and 1M completed requests.

4. Resilience Behavior
   - Baseline (no faults), delay injection, and instance kill/restart scenarios.
   - Verify expected qualitative responses (degraded latency, recovery timelines).

5. External Baseline (MiSim)
   - Optional CSV-level comparison for overlapping metric files.
   - Comparison is used to explain divergence, not to force API or architecture coupling.

## Required Run Metadata

Every benchmark case must record:

- seed
- config hash
- git commit hash
- case name
- wall-clock runtime seconds
- completed and failed request counts

## Default Runner

Use:

```bash
python -m experiments.runners.benchmark_runner
```

The runner reads:

- `experiments/configs/benchmark_suite.json`

and writes per-case artifacts under:

- `analysis/metrics/benchmark_run/`

including JSON metadata, metrics, MiSim-style CSV exports, and a suite report.
