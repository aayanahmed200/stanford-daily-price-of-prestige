# The Price of Prestige - reproducible pipeline
# Targets mirror the pipeline steps; see docs/methods.md for details.

PYTHON ?= python
QUARTO ?= quarto

.PHONY: all download validate preprocess analysis visualization pipeline release-data tests lint render render-article render-notebook clean

## Run the entire analysis pipeline (download -> report).
all: pipeline

## Step 1 - fetch raw data (Scorecard + CPI). ~0.5 GB the first time.
download:
	$(PYTHON) -m scripts.download

## Step 2 - data-quality checks on raw inputs.
validate:
	$(PYTHON) -m scripts.validate

## Step 3 - clean, merge, and inflation-adjust the data.
preprocess:
	$(PYTHON) -m scripts.preprocess

## Step 4 - compute all statistics and write outputs/results.json.
analysis:
	$(PYTHON) -m scripts.analysis

## Step 5 - render all figures to figures/.
visualization:
	$(PYTHON) -m scripts.visualization

## Run steps 1-5 in order.
pipeline: download validate preprocess analysis visualization

## Refresh the committed derived data (data/processed, outputs, figures).
## Commit the resulting diff; this is what the GitHub Pages build uses.
release-data: pipeline

## Run the test suite.
tests:
	$(PYTHON) -m pytest

## Lint the source.
lint:
	$(PYTHON) -m ruff check scripts tests

## Render the article and notebook to HTML.
render: render-article render-notebook

render-article:
	$(QUARTO) render index.qmd

render-notebook:
	$(QUARTO) render notebooks/notebook.qmd

## Remove pipeline outputs (keeps raw downloads).
clean:
	-$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in (pathlib.Path('figures'), pathlib.Path('outputs'), pathlib.Path('data/processed'))]"
