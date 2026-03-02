# Escher

Escher is an extensible discrete-event simulator for resilience-aware microservice experiments.

## Current bootstrap status

- SimPy-backed engine adapter in `core/`
- Basic workload generator and dependency model
- Initial resilience mechanisms in `model/resilience/`
- Config-driven smoke scenario runner in `experiments/runners/smoke_runner.py`
- Canonical experiment schema example in `experiments/configs/v1_contract_example.json`
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
