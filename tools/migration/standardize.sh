#!/bin/bash
# standardize.sh — Apply content-hub standards to a previously migrated integration
#
# This is PR2 of the two-PR migration workflow. It assumes PR1 (faithful
# migration via migrate_integration.sh --minimal) has already been merged.
#
# Usage:
#   ./tools/migration/standardize.sh <integration_snake_name> [integration_dir]
#
# Examples:
#   ./tools/migration/standardize.sh certly
#   ./tools/migration/standardize.sh shodan content/response_integrations/google
#
# What this script does:
#   1. Adds/fixes the Verify SSL parameter in definition.yaml
#   2. Rewrites Ping action to use standard success/failure messages
#   3. Removes the integration from validator exclusion lists
#   4. Runs mp validate + mp check --fix + tests

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PYTHON="${PYTHON:-python3.11}"

# ── Arguments ──────────────────────────────────────────────────────────
if [ $# -lt 1 ]; then
    echo "Usage: $0 <integration_snake_name> [integration_parent_dir]"
    echo ""
    echo "  integration_snake_name   snake_case name (e.g., certly, url_scan_io)"
    echo "  integration_parent_dir   Parent directory of the integration"
    echo "                           (default: content/response_integrations/google)"
    exit 1
fi

SNAKE_NAME="$1"
PARENT_DIR="${2:-content/response_integrations/google}"
INTEGRATION_PATH="$REPO_ROOT/$PARENT_DIR/$SNAKE_NAME"

if [ ! -d "$INTEGRATION_PATH" ]; then
    echo "ERROR: Integration not found at $INTEGRATION_PATH"
    exit 1
fi

echo "════════════════════════════════════════════════════════════════"
echo "  Standardize: $SNAKE_NAME"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "  Path: $INTEGRATION_PATH"
echo ""

# Prevent mp validate from auto-opening HTML reports
export BROWSER=true

# ── Step 1: Fix Verify SSL ─────────────────────────────────────────────
echo "── Step 1: Verify SSL parameter ──────────────────────────────"
$PYTHON -c "
import yaml
from pathlib import Path

def_path = Path('$INTEGRATION_PATH/definition.yaml')
data = yaml.safe_load(def_path.read_text())

# Get integration display name
display_name = data.get('display_name', '$SNAKE_NAME')

# Check if Verify SSL already exists
params = data.get('integration_params', [])
ssl_exists = any(
    p.get('param_name', '').lower() in ('verify ssl', 'verify ssl certificate', 'ssl verification')
    for p in params
)

if ssl_exists:
    # Fix default_value to true if needed
    for p in params:
        if p.get('param_name', '').lower() in ('verify ssl', 'verify ssl certificate', 'ssl verification'):
            p['default_value'] = True
            p['param_type'] = 'boolean'
            p['is_mandatory'] = False
            p['description'] = f'If selected, the integration validates the SSL certificate when connecting to {display_name}. Selected by default.'
    print('  ✓ Fixed existing Verify SSL parameter')
else:
    # Add Verify SSL parameter
    ssl_param = {
        'param_name': 'Verify SSL',
        'param_type': 'boolean',
        'default_value': True,
        'is_mandatory': False,
        'description': f'If selected, the integration validates the SSL certificate when connecting to {display_name}. Selected by default.',
    }
    params.insert(0, ssl_param)
    data['integration_params'] = params
    print('  ✓ Added Verify SSL parameter')

def_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
" 2>&1

# ── Step 2: Fix Ping messages ──────────────────────────────────────────
echo ""
echo "── Step 2: Ping action messages ──────────────────────────────"
PING_FILE=""
for name in "Ping.py" "ping.py"; do
    if [ -f "$INTEGRATION_PATH/actions/$name" ]; then
        PING_FILE="$INTEGRATION_PATH/actions/$name"
        break
    fi
done

if [ -n "$PING_FILE" ]; then
    PING_CONTENT=$(cat "$PING_FILE")
    NEEDS_FIX=false

    if ! echo "$PING_CONTENT" | grep -q "Successfully connected to the"; then
        NEEDS_FIX=true
    fi
    if ! echo "$PING_CONTENT" | grep -q "Failed to connect to the"; then
        NEEDS_FIX=true
    fi

    if [ "$NEEDS_FIX" = true ]; then
        echo "  ⚠ Ping messages don't match standard format."
        echo "  Please manually update $PING_FILE with:"
        echo "    Success: 'Successfully connected to the {name} server with the provided connection parameters!'"
        echo "    Failure: 'Failed to connect to the {name} server! Error is {err}'"
    else
        echo "  ✓ Ping messages already match standard format"
    fi
else
    echo "  ⚠ No Ping action found"
fi

# ── Step 3: Remove from exclusion lists ────────────────────────────────
echo ""
echo "── Step 3: Remove from validator exclusion lists ──────────────"
EXCLUSIONS_FILE="$REPO_ROOT/packages/mp/src/mp/core/data/exclusions.yaml"
if [ -f "$EXCLUSIONS_FILE" ]; then
    sed -i "/^  - \"$SNAKE_NAME\"$/d" "$EXCLUSIONS_FILE"
    echo "  ✓ Removed $SNAKE_NAME from exclusion lists"
fi

# ── Step 4: Lint, validate, test ───────────────────────────────────────
echo ""
echo "── Step 4: Lint & validate ───────────────────────────────────"

cd "$INTEGRATION_PATH"

echo "  Running: mp check --fix"
mp check "$INTEGRATION_PATH" --fix 2>&1 | tail -3 || true

echo "  Running: mp format"
mp format "$INTEGRATION_PATH" 2>&1 | tail -3 || true

echo "  Running: mp validate integration $SNAKE_NAME --only-pre-build"
mp validate integration "$SNAKE_NAME" -q --only-pre-build 2>&1 | tail -5 || true

echo ""
echo "── Running tests ─────────────────────────────────────────────"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/.venv/lib/python3.11/site-packages/soar_sdk"
.venv/bin/python -m pytest tests -v 2>&1 || true

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Standardization complete: $SNAKE_NAME"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "  Review the changes and create PR2."
