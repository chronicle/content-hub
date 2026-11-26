# `mp self`

Manage the `mp` CLI installation itself.

## Usage

```bash
mp self update
```

## Subcommands

### `update`

Upgrades `mp` in its current Python environment to the latest commit on `main` (`git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp`) using `uv pip install --upgrade`.

```bash
mp self update
```

> [!TIP]
> If you installed `mp` via `uv tool install`, you can also run `uv tool upgrade mp`. When working on local changes inside `packages/mp`, invoke `uv run --project packages/mp mp ...` instead so you do not overwrite your local checkout with `main`.
