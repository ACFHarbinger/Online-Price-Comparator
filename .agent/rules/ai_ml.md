# AI / ML Rules

- Pin model/framework versions explicitly (no floating `latest` tags) — reproducibility matters more than always having the newest release.
- Every training run must be reproducible from a config file (Hydra/YAML/JSON) checked into `configs/`; never hardcode hyperparameters in code.
- Log metrics to a tracked experiment store (e.g. MLflow, Weights & Biases, or a local `reports/` CSV) — not just stdout.
- Keep data loading, model definition, training loop, and evaluation in separate modules so any one piece can be swapped independently.
- Large artifacts (checkpoints, datasets) never go in git — use `.gitignore` and document the retrieval path in `docs/`.
