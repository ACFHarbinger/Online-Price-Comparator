# Workflow: AI/ML Experiment

1. Define the experiment config (data, model, hyperparameters) in `configs/` before writing code.
2. Run a small-scale smoke test (few steps/epochs, tiny data slice) to catch shape/dtype errors cheaply.
3. Launch the full run with experiment tracking enabled; record the config alongside the run.
4. Evaluate against a held-out set using the same metric the project already tracks — don't introduce a new metric ad hoc.
5. Compare against the previous best run before claiming an improvement.
