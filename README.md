# Escher

Escher is an extensible discrete-event simulator for resilience-aware microservice experiments.

## Current bootstrap status

- SimPy-backed engine adapter in `core/`
- Basic workload generator and dependency model
- Initial resilience mechanisms in `model/resilience/`
- Config-driven smoke scenario runner in `experiments/runners/smoke_runner.py`
- Canonical experiment schema example in `experiments/configs/v1_contract_example.json`
- Sequential service/operation dependency execution from canonical config
- First-class `kill_instance` and `summon_instance` faultloads for service availability events
- Determinism, edge-case, and stress tests in `tests/`

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m experiments.runners.smoke_runner
python -m unittest discover -s tests
```

The default runner reads `experiments/configs/smoke_scenario.json` using the canonical layout (`simulation_metadata`, `services`, `workloads`, `faultloads`, `policies`).

Latency values are reported in simulation time units (STU). Configure `simulation_metadata.time_unit` to declare the mapping, e.g., `1 STU = 1 second`.

Escher benchmark standards are documented in `BENCHMARK_STANDARD.md`. Run the default benchmark suite with:

```bash
python -m experiments.runners.benchmark_runner
```

Each run writes reproducibility artifacts to `analysis/metrics/smoke_run/`:

- `run_metadata.json` with seed, config hash, and git commit hash
- `run_metrics.json` with the computed output metrics
- MiSim-style CSV metrics:
  - `GEN_ALL_SuccessfulRequests.csv`
  - `GEN_ALL_FailedRequests.csv`
  - `R[All]_ResponseTimes.csv`
  - `R[<EndpointRef>]_ResponseTimes.csv`
  - `S[<ServiceName>]_InstanceCount.csv`
  - `CB[<BreakerName>]_StateTimeline.csv`

For cross-tool output checks, compare Escher and MiSim CSV folders with:

```bash
python -m analysis.metrics.comparison analysis/metrics/smoke_run /path/to/misim/csv
```
