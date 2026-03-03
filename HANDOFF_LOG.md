# Escher Handoff Log

## Latest Update (Rolling)

- Policy: append one bullet block here at the end of every completed checkpoint.
- 2026-03-02: Added structured handoff log format and recorded full session progress, validation status, git snapshot, and ordered TODOs for the next agent.

## 2026-03-02 Session Log

### [01] Repository and project setup
- Created `Escher/` and scaffolded project layout: `core/`, `model/`, `experiments/`, `analysis/`, `tests/`.
- Initialized git in `Escher`.
- Added `.gitignore` and initial project plan `V1-PLAN.md`.
- Connected and pushed repo to `https://github.com/psh0078/Escher`.

### [02] Core runtime bootstrap
- Added package/dependency config in `pyproject.toml`.
- Implemented engine abstractions and SimPy adapter:
  - `core/engine.py`
  - `core/simpy_engine.py`
  - `core/clock.py`
  - `core/event_queue.py`

### [03] Initial modeling/resilience modules
- Added deterministic RNG utility: `model/rng.py`.
- Added resilience modules:
  - `model/resilience/retry.py`
  - `model/resilience/circuit_breaker.py`
  - `model/resilience/connection_limiter.py`
  - `model/resilience/load_balancer.py`
  - `model/resilience/autoscaler.py`
- Added workload/dependency primitives:
  - `model/workloads/generators.py`
  - `model/resources/dependency.py`

### [04] Runner + tests bootstrap
- Added runner and smoke config:
  - `experiments/runners/smoke_runner.py`
  - `experiments/configs/smoke_scenario.json`
- Added metrics collector:
  - `analysis/metrics/collector.py`
- Added tests:
  - `tests/test_engine.py`
  - `tests/test_smoke_runner.py`

### [05] Canonical schema migration
- Added architecture contract doc: `ARCHITECTURE.md`.
- Added canonical config example: `experiments/configs/v1_contract_example.json`.
- Migrated runner/config parsing to canonical schema sections:
  - `simulation_metadata`
  - `services`
  - `workloads`
  - `faultloads`
  - `policies`

### [06] Output readability and units
- Added human-readable run summary in `smoke_runner.py`.
- Added explicit time unit declaration support via `simulation_metadata.time_unit`.
- Updated docs (`README.md`) to clarify STU mapping.

### [07] Reproducibility artifacts
- Added artifact writes in runner:
  - `analysis/metrics/smoke_run/run_metadata.json`
  - `analysis/metrics/smoke_run/run_metrics.json`
- Metadata includes required fields:
  - `seed`
  - `config_hash`
  - `git_commit_hash`

### [08] MiSim-style CSV export
- Added exporter: `analysis/metrics/exporter.py`.
- Added CSV outputs:
  - `GEN_ALL_SuccessfulRequests.csv`
  - `GEN_ALL_FailedRequests.csv`
  - `R[All]_ResponseTimes.csv`
  - `S[<ServiceName>]_InstanceCount.csv`

### [09] Execution-model upgrade
- Added config-driven service graph model:
  - `model/resources/service_graph.py`
- Runner now executes sequential operation dependencies from canonical service graph.

### [10] Faultload extension: kill instance
- Added first-class `kill_instance` handling in canonical `faultloads`.
- Added instance timeline tracking in metrics collector and CSV exporter.
- Updated configs to include dependency chain + delay injection + kill event.

### [11] Validation run status
- Tests pass with:
  - `python3 -m unittest discover -s tests`
- Smoke run executes and produces:
  - human-readable summary
  - metadata and metrics JSON artifacts
  - MiSim-style CSV artifacts

### [12] Last observed smoke behavior
- Request failures reported as `0` in latest run.
- Latency percentiles changed relative to earlier run due to:
  - sequential dependency graph execution
  - latency injection as delay (not forced outage)
  - retries recovering transient failures
  - `kill_instance` reducing service count but not reducing to zero

---

## Git Snapshot At Handoff

### Recent commits
- `0f4395a` Adopt canonical config schema for smoke runner
- `509a058` Bootstrap Escher simulator scaffold with deterministic smoke flow
- `9dd6e4e` Initialize Escher with baseline project plan

### Working tree at handoff
- Branch: `main`
- Status observed earlier: ahead of `origin/main` by 2 commits, plus local uncommitted changes from current in-progress checkpoint.

---

## Next Agent TODO (ordered)

1. Commit all current local changes as a single checkpoint.
2. Add `summon_instance` (restart) faultload.
3. Add circuit-breaker state timeline CSV output (`CB[...]`).
4. Add per-endpoint response time CSV (`R[<Endpoint>]_ResponseTimes.csv`).
5. Add Escher-vs-MiSim comparison utility over CSV files.

## 2026-03-03 Session Log

### [13] Faultload extension: summon instance
- Added first-class `summon_instance` handling in canonical `faultloads` parsing and scheduling.
- Runner now supports both scale-down (`kill_instance`) and scale-up (`summon_instance`) events with timeline tracking.

### [14] Metrics export extension
- Added circuit breaker state timeline recording and export:
  - `CB[global]_StateTimeline.csv`
- Added per-endpoint response time recording and export:
  - `R[<EndpointRef>]_ResponseTimes.csv`

### [15] Escher-vs-MiSim CSV comparison utility
- Added `analysis/metrics/comparison.py` with:
  - directory-level CSV comparison
  - tolerance-aware numeric value checks
  - CLI entrypoint via `python -m analysis.metrics.comparison <escher_dir> <misim_dir>`

### [16] Validation run status
- Tests pass with:
  - `python3 -m unittest discover -s tests`
- Smoke run executes and now emits endpoint + circuit-breaker CSV artifacts.
- Comparison utility validated against identical directories (`MATCH`).
