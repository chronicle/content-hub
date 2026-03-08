# Legacy Integration Describer

A CLI tool for parsing integration definitions from multiple local repositories, extracting historical Git versions natively, and generating cohesive AI metadata overviews into CSVs via `mp describe action`.

## Prerequisites

- `uv` package manager installed
- Python 3.11+
- Local Google SecOps target repositories appropriately cloned or available

## Setup

1. Clone this repository locally or initialize the local virtual environment via `uv`:
   ```sh
   uv sync
   ```
2. The project relies on dynamic `mp` framework dependencies securely loaded via GitHub alongside robust native Pytest/Ruff static analyzers!

## Usage

Simply run the application dynamically natively managed via `uv`:

```sh
uv run legacy-integration-describer \
    --tip-marketplace ~/repos/tip-marketplace \
    --content-hub ~/PycharmProjects/content-hub \
    --tip-marketplace-uncertified ~/repos/tip-marketplace-uncertified \
    --source ./inputs \
    --destination ./outputs
```

All flags are optional. By dropping directory definitions that you don't possess locally, it will naturally exclude those specific git object validations when searching for active matches! By default, the tool will consume files cleanly inside recursive local `./inputs` tracking targets gracefully natively into per-partner isolated namespaces nested strictly inside `./outputs/<partner_name>/`.

Outputs are seamlessly persisted into `outputs/` under identically structured `<partner>_output.csv` alongside missing integration exception listings detailed under `<partner>_errors.txt`.
