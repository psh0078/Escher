# Escher Study Plan

This plan is for a focused code study session before major new implementation work.

## How to Use This Plan

- Work through checkpoints in order.
- At each checkpoint, run the listed quick verification command(s).
- Stop after each checkpoint and write a short note in your own words.

## Checkpoint 0: Session Bootstrap

1. Read `HANDOFF_LOG.md`.
2. Read this file (`STUDY_PLAN.md`).
3. Confirm current repo status:

```bash
git status --short --branch
```

## Checkpoint 1: Integration-First Runtime Trace

Primary file:

- `experiments/runners/smoke_runner.py`

Study focus:

- `run_scenario(...)` lifecycle
- request arrival flow
- dependency recursion flow
- retry + circuit-breaker interactions
- kill/summon event effects
- metrics recording points

Quick verification:

```bash
python3 -m experiments.runners.smoke_runner
```

Expected:

- human summary prints
- run artifacts appear in `analysis/metrics/smoke_run/`

## Checkpoint 2: Core Engine Semantics

Primary files:

- `core/engine.py`
- `core/simpy_engine.py`
- `core/event_queue.py`
- `core/clock.py`

Study focus:

- scheduling contract and invariants
- time advancement boundaries (`run()` only)
- event observability hooks
- backend replaceability boundary

Quick verification:

```bash
python3 -m unittest tests/test_engine.py
```

## Checkpoint 3: Scenario Schema and Parsing

Primary files:

- `experiments/configs/smoke_scenario.json`
- `experiments/runners/smoke_runner.py` (`parse_canonical_config` and parsers)

Study focus:

- canonical schema sections
- parser validation rules
- faultload parsing (`delay_injection`, `kill_instance`, `summon_instance`)
- service graph construction

Quick verification:

```bash
python3 -m unittest tests/test_smoke_runner.py
```

## Checkpoint 4: Resilience Modules (Isolated)

Primary files:

- `model/resilience/retry.py`
- `model/resilience/circuit_breaker.py`
- `model/resilience/connection_limiter.py`
- `model/resilience/load_balancer.py`
- `model/resilience/autoscaler.py`

Study focus:

- policy responsibilities
- deterministic behavior
- what is currently wired vs not wired in runner

Quick verification:

- Confirm usage sites from runner and tests.

## Checkpoint 5: Metrics, Artifacts, and Comparison

Primary files:

- `analysis/metrics/collector.py`
- `analysis/metrics/exporter.py`
- `analysis/metrics/comparison.py`
- `tests/test_run_artifacts.py`

Study focus:

- request-level vs endpoint-level metrics
- instance timeline and breaker timeline logs
- CSV format guarantees
- mismatch diagnostics in directory comparison

Quick verification:

```bash
python3 -m unittest tests/test_run_artifacts.py
python3 -m analysis.metrics.comparison analysis/metrics/smoke_run analysis/metrics/smoke_run
```

## Checkpoint 6: Benchmark Framework and COSIMO Readiness

Primary files:

- `BENCHMARK_STANDARD.md`
- `experiments/configs/benchmark_suite.json`
- `experiments/runners/benchmark_runner.py`
- `tests/test_benchmark_runner.py`

Study focus:

- benchmark case model and overrides
- determinism repeat checks
- throughput/runtime report structure
- optional MiSim CSV comparison hook

Quick verification:

```bash
python3 -m experiments.runners.benchmark_runner
python3 -m unittest tests/test_benchmark_runner.py
```

## Final Study Output (What to Produce)

After all checkpoints, produce a short note with:

1. Current architecture strengths
2. Top 3 correctness risks
3. Top 3 performance/modeling gaps for COSIMO
4. Next implementation checkpoint to execute

## Recommended New-Session Prompt

Use this in your new session:

"Read `HANDOFF_LOG.md` and `STUDY_PLAN.md`, then guide me through the study checkpoints one by one with code references and stop after each checkpoint for my confirmation."
