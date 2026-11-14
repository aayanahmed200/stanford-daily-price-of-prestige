# Contributing

Thanks for wanting to improve **The Price of Prestige**. This is a data
journalism project, so contributions can be analysis, writing, figures, or
infrastructure.

## Code of conduct

This project is governed by the Contributor Covenant (see
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)). Be kind, cite your sources, and
assume good faith.

## Getting started

```bash
git clone https://github.com/aayanahmed200/stanford-daily-price-of-prestige.git
cd stanford-daily-price-of-prestige
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
pre-commit install
```

## Workflow

1. Open an issue or PR describing what you are changing and why.
2. Branch off `main` (`git checkout -b fix/fancy-name`).
3. Make small, focused commits with descriptive messages.
4. Run the checks before pushing:
   ```bash
   python -m ruff check scripts tests
   python -m pytest
   ```
5. Open a pull request. CI runs lint and tests automatically.

## Data and reproducibility

- Raw data is **not** committed; run `python -m scripts.download` to fetch it
  (the historical archive is ~0.5 GB).
- Every statistic quoted in the article must come from
  `outputs/results.json`, which the pipeline regenerates.
- Never hand-write numbers into the article — use the `results.json` block in
  `index.qmd` so figures and prose stay in sync.
- If you change an analysis assumption, update `scripts/config.py`,
  `docs/methods.qmd`, and re-run the full pipeline
  (`python -m scripts.download && python -m scripts.validate && python -m
  scripts.preprocess && python -m scripts.analysis && python -m
  scripts.visualization`).

## Adding a figure

- Figures are produced by `scripts/visualization.py` and saved to `figures/`.
- Keep the house style: Okabe-Ito color-blind-safe palette and the
  `apply_style()` defaults in `scripts/helpers.py`.

## Tests

Tests live in `tests/` and must not require network access -- every existing
test runs against synthetic or already-processed data. There is no
`tests/integration/` directory yet. If you add a test that needs the ~0.5 GB
downloads, keep it out of the default suite: give it a clearly-named module
(e.g. `tests/integration/`) and a registered pytest marker (e.g.
`needs_network`, added to `[tool.pytest.ini_options]` in `pyproject.toml`) so
`pytest -m "not needs_network"` (or a similar default) can skip it in CI.
