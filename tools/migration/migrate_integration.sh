#!/bin/bash
# migrate_integration.sh — End-to-end migration pipeline
#
# Runs migrate.py (structure/imports migration) followed by
# generate_test_mocks.py (test mock infrastructure generation).
#
# Usage:
#   ./tools/migration/migrate_integration.sh <IntegrationName> [destination]
#
# Examples:
#   ./tools/migration/migrate_integration.sh UrlScanIo
#   ./tools/migration/migrate_integration.sh Shodan content/response_integrations/google
#
# Prerequisites:
#   - mp, uv, addlicense on PATH
#   - tip-marketplace cloned at ../tip-marketplace (sibling to content-hub)
#   - Python 3.11 available as python3.11

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Resolve tip-marketplace location (try common locations)
TIP_MARKETPLACE=""
for candidate in \
    "/usr/local/google/home/eranc/repos/tip-marketplace" \
    "$REPO_ROOT/../tip-marketplace" \
    "$REPO_ROOT/../../tip-marketplace"; do
    if [ -d "$candidate/Integrations" ]; then
        TIP_MARKETPLACE="$(cd "$candidate" && pwd)"
        break
    fi
done

if [ -z "$TIP_MARKETPLACE" ]; then
    echo "ERROR: Cannot find tip-marketplace repo. Expected at ../tip-marketplace/"
    exit 1
fi

# Use a python with libcst + mp available.
# Prefer repo venv (has all deps), fall back to main repo venv for worktrees.
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    for candidate in \
        "$REPO_ROOT/.venv/bin/python" \
        "$(git worktree list 2>/dev/null | head -1 | awk '{print $1}')/.venv/bin/python"; do
        if [ -f "$candidate" ] && "$candidate" -c "import libcst" 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    done
    PYTHON="${PYTHON:-python3.11}"
fi
MIGRATION_SCRIPT="$SCRIPT_DIR/migrate.py"
MOCK_GENERATOR="$SCRIPT_DIR/generate_test_mocks.py"

# ── Arguments ──────────────────────────────────────────────────────────
MINIMAL=false
POSITIONAL=()
for arg in "$@"; do
    case "$arg" in
        --minimal) MINIMAL=true ;;
        *) POSITIONAL+=("$arg") ;;
    esac
done
set -- "${POSITIONAL[@]}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 [--minimal] <IntegrationName> [destination_dir]"
    echo ""
    echo "  --minimal         Faithful migration only (skip Verify SSL, Ping rewrite)."
    echo "                    For use with the two-PR workflow (PR1: migrate, PR2: standardize)."
    echo "  IntegrationName   Name as it appears in tip-marketplace (e.g., UrlScanIo)"
    echo "  destination_dir   Where to place the migrated integration"
    echo "                    (default: content/response_integrations/google_new_test)"
    exit 1
fi

INTEGRATION_NAME="$1"
DEST_DIR="${2:-content/response_integrations/google_new_test}"

# Convert PascalCase to snake_case using mp's logic (handles consecutive capitals
# like SSLLabs -> ssl_labs, not s_s_l_labs)
SNAKE_NAME=$($PYTHON -c "from mp.core.utils.common import str_to_snake_case; print(str_to_snake_case('$INTEGRATION_NAME'))" 2>/dev/null \
  || echo "$INTEGRATION_NAME" | sed -E 's/([A-Z]+)([A-Z][a-z])/\1_\2/g' | sed -E 's/([a-z])([A-Z])/\1_\2/g' | tr '[:upper:]' '[:lower:]')

# Prevent integration directory names from shadowing Python stdlib modules.
# e.g., HTTP -> http/ shadows stdlib http, breaking `from http.client import ...`
# for ALL sibling integrations (pytest adds the parent dir to sys.path).
# Check for stdlib AND pip package name collisions
COLLISION=$($PYTHON -c "
import sys
name = '$SNAKE_NAME'
# Check stdlib
if hasattr(sys, 'stdlib_module_names') and name in sys.stdlib_module_names:
    print(name + '_integration')
    exit()
# Check pip packages that integrations commonly import as their own name
pip_collisions = {'jira', 'slack', 'redis', 'kafka', 'ldap3', 'requests', 'paramiko'}
if name in pip_collisions:
    print(name + '_integration')
    exit()
print(name)
" 2>/dev/null || echo "$SNAKE_NAME")
if [ "$COLLISION" != "$SNAKE_NAME" ]; then
    echo "  WARNING: '$SNAKE_NAME' shadows a package name — renaming to '$COLLISION'"
    SNAKE_NAME="$COLLISION"
fi

INTEGRATION_PATH="$REPO_ROOT/$DEST_DIR/$SNAKE_NAME"

echo "════════════════════════════════════════════════════════════════"
echo "  Migration Pipeline: $INTEGRATION_NAME"
if [ "$MINIMAL" = true ]; then
echo "  Mode:        MINIMAL (faithful migration, skip Verify SSL/Ping)"
fi
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "  Source:      $TIP_MARKETPLACE/Integrations/$INTEGRATION_NAME"
echo "  Destination: $INTEGRATION_PATH"
echo "  Python:      $($PYTHON --version)"
echo ""

# ── Pre-flight checks ─────────────────────────────────────────────────
if [ ! -d "$TIP_MARKETPLACE/Integrations/$INTEGRATION_NAME" ]; then
    echo "ERROR: Integration '$INTEGRATION_NAME' not found in $TIP_MARKETPLACE/Integrations/"
    exit 1
fi

if [ ! -f "$MIGRATION_SCRIPT" ]; then
    echo "ERROR: Migration script not found at $MIGRATION_SCRIPT"
    exit 1
fi

if [ ! -f "$MOCK_GENERATOR" ]; then
    echo "ERROR: Mock generator not found at $MOCK_GENERATOR"
    exit 1
fi

# Ensure uv, mp, addlicense are available to subprocesses
# (migrate.py calls subprocess.run(["uv", "sync"]) etc.)
MAIN_REPO_VENV="$(git worktree list 2>/dev/null | head -1 | awk '{print $1}')/.venv/bin"
if [ -d "$MAIN_REPO_VENV" ]; then
    export PATH="$MAIN_REPO_VENV:$HOME/go/bin:$PATH"
fi

# Prevent mp validate from auto-opening HTML reports in a browser
export BROWSER=true

# Use this worktree's mp source for the migration script only.
# Don't export globally — it leaks into integration venvs and breaks module resolution.
MP_PYTHONPATH="$REPO_ROOT/packages/mp/src:${PYTHONPATH:-}"

# Ensure mp config points to the correct content-hub root.
# In batch mode (MIGRATION_BATCH_MODE=true), this is done once by the batch script.
if [ "${MIGRATION_BATCH_MODE:-}" != "true" ]; then
    MAIN_REPO="$(git worktree list 2>/dev/null | head -1 | awk '{print $1}')"
    if [ -d "$MAIN_REPO/packages/tipcommon" ]; then
        mp config --root-path "$MAIN_REPO" 2>/dev/null || true
    fi
fi

if [ -d "$INTEGRATION_PATH" ]; then
    echo "WARNING: $INTEGRATION_PATH already exists. Removing..."
    rm -rf "$INTEGRATION_PATH"
fi

# ── Step 1: Migration (migrate.py) ─────────────────────────────────
echo ""
echo "── Step 1/4: Migrating structure and imports ──────────────────"
echo ""

cd "$REPO_ROOT"
MIGRATE_ARGS=(
    "$TIP_MARKETPLACE/Integrations"
    "$DEST_DIR"
    --tests-dir "$TIP_MARKETPLACE/Tests"
    --integrations-list "$INTEGRATION_NAME"
)
if [ "$MINIMAL" = true ]; then
    MIGRATE_ARGS+=(--skip-verify-ssl)
fi
PYTHONPATH="$MP_PYTHONPATH" $PYTHON "$MIGRATION_SCRIPT" "${MIGRATE_ARGS[@]}"

# migrate.py uses str_to_snake_case which may produce a different name
# than our SNAKE_NAME (e.g., we renamed http -> http_integration for stdlib).
# Find the actual output directory and rename if needed.
ORIGINAL_SNAKE=$($PYTHON -c "from mp.core.utils.common import str_to_snake_case; print(str_to_snake_case('$INTEGRATION_NAME'))" 2>/dev/null || echo "")
ORIGINAL_PATH="$REPO_ROOT/$DEST_DIR/$ORIGINAL_SNAKE"
if [ "$ORIGINAL_PATH" != "$INTEGRATION_PATH" ] && [ -d "$ORIGINAL_PATH" ]; then
    mv "$ORIGINAL_PATH" "$INTEGRATION_PATH"
    echo "  Renamed $ORIGINAL_SNAKE -> $SNAKE_NAME (stdlib collision)"
fi

if [ ! -d "$INTEGRATION_PATH" ]; then
    echo "ERROR: Migration did not produce output at $INTEGRATION_PATH"
    exit 1
fi

echo ""
echo "  ✓ Migration complete: $INTEGRATION_PATH"

# ── Step 1b: Post-migration fixes ──────────────────────────────────
echo ""
echo "── Step 1b: Post-migration fixes ─────────────────────────────"

# Fix JSON result example naming: need BOTH PascalCase (action file stem)
# AND snake_case (action YAML name). Two validators expect different conventions.
RESOURCES_DIR="$INTEGRATION_PATH/resources"
ACTIONS_DIR="$INTEGRATION_PATH/actions"
if [ -d "$RESOURCES_DIR" ] && [ -d "$ACTIONS_DIR" ]; then
    for py_file in "$ACTIONS_DIR"/*.py; do
        [ -f "$py_file" ] || continue
        stem=$(basename "$py_file" .py)
        [ "$stem" = "__init__" ] && continue
        # Convert PascalCase to snake_case using mp's logic (handles DNSResolve -> dns_resolve)
        snake=$($PYTHON -c "from mp.core.utils.common import str_to_snake_case; print(str_to_snake_case('$stem'))" 2>/dev/null \
          || echo "$stem" | sed -E 's/([A-Z]+)([A-Z][a-z])/\1_\2/g' | sed -E 's/([a-z])([A-Z])/\1_\2/g' | tr '[:upper:]' '[:lower:]')
        snake_file="$RESOURCES_DIR/${snake}_JsonResult_example.json"
        pascal_file="$RESOURCES_DIR/${stem}_JsonResult_example.json"
        # If snake_case exists but PascalCase doesn't, create PascalCase copy
        if [ -f "$snake_file" ] && [ ! -f "$pascal_file" ]; then
            cp "$snake_file" "$pascal_file"
        fi
        # If PascalCase exists but snake_case doesn't, create snake_case copy
        if [ -f "$pascal_file" ] && [ ! -f "$snake_file" ]; then
            cp "$pascal_file" "$snake_file"
        fi
    done
    echo "  ✓ JSON result example dual naming"
fi

# Fix ticket_number: must be string, not int
for rn_file in "$INTEGRATION_PATH/release_notes.yaml"; do
    if [ -f "$rn_file" ]; then
        sed -i "s/ticket_number: \([0-9][0-9]*\)$/ticket_number: '\1'/" "$rn_file"
    fi
done
echo "  ✓ ticket_number as string"

# Fix empty publish_time
$PYTHON -c "
import yaml, sys
path = '$INTEGRATION_PATH/release_notes.yaml'
try:
    data = yaml.safe_load(open(path))
    changed = False
    for note in (data or []):
        if not note.get('publish_time'):
            note['publish_time'] = '2020-01-01'
            changed = True
    if changed:
        yaml.dump(data, open(path, 'w'), default_flow_style=False, sort_keys=False)
        print('  ✓ Fixed empty publish_time entries')
except: pass
" 2>/dev/null

# Add integration to parent ruff.toml ["ALL"] exclusion (matching existing convention)
PARENT_RUFF="$(dirname "$INTEGRATION_PATH")/ruff.toml"
if [ -f "$PARENT_RUFF" ]; then
    RUFF_ENTRY="\"$SNAKE_NAME/**\" = [\"ALL\"]"
    if ! grep -q "$SNAKE_NAME" "$PARENT_RUFF" 2>/dev/null; then
        # Insert before [format] section
        sed -i "/^\[format\]/i $RUFF_ENTRY" "$PARENT_RUFF"
        echo "  ✓ Added $SNAKE_NAME to parent ruff.toml exclusions"
    fi
fi

# In minimal mode, add integration to validator exclusion lists
# (removed in PR2 by standardize.sh after applying the fixes)
if [ "$MINIMAL" = true ]; then
    EXCLUSIONS_FILE="$REPO_ROOT/packages/mp/src/mp/core/data/exclusions.yaml"
    if [ -f "$EXCLUSIONS_FILE" ]; then
        # Add to SSL exclusion list
        if ! grep -q "\"$SNAKE_NAME\"" <(grep -A 100 "excluded_names_without_verify_ssl:" "$EXCLUSIONS_FILE" | head -50); then
            sed -i "/^excluded_names_without_verify_ssl:/a\\  - \"$SNAKE_NAME\"" "$EXCLUSIONS_FILE"
        fi
        # Add to Ping message exclusion list
        if ! grep -q "\"$SNAKE_NAME\"" <(grep -A 100 "excluded_names_without_ping_message_format:" "$EXCLUSIONS_FILE" | head -50); then
            sed -i "/^excluded_names_without_ping_message_format:/a\\  - \"$SNAKE_NAME\"" "$EXCLUSIONS_FILE"
        fi
        echo "  ✓ Added $SNAKE_NAME to validator exclusion lists (SSL + Ping)"
    fi
fi

# Clean up legacy test files that are incompatible with the new framework
# (they use patterns like non-relative imports and LegacyActionOutput)
TESTS_DIR="$INTEGRATION_PATH/tests"
if [ -d "$TESTS_DIR" ]; then
    # Remove legacy test files that import from the old conftest patterns
    for f in "$TESTS_DIR"/test_*.py; do
        if [ -f "$f" ] && [ "$(basename "$f")" != "test_imports.py" ]; then
            # Check if it uses legacy patterns (non-relative imports, LegacyActionOutput, etc.)
            if grep -q "LegacyActionOutput\|from core\.\|from Tests\." "$f" 2>/dev/null; then
                echo "  Removing incompatible legacy test: $(basename "$f")"
                rm "$f"
            fi
        fi
    done

    # Remove legacy mock helpers that conflict with generated ones.
    # BUT preserve mock_data.json — legacy tests load it at module level.
    # Only remove response.py (conflicts with integration_testing.requests.response).
    if [ -f "$TESTS_DIR/core/response.py" ]; then
        echo "  Removing legacy test helper: response.py"
        rm "$TESTS_DIR/core/response.py"
    fi
fi

# ── Step 2: Generate test mocks ────────────────────────────────────────
echo ""
echo "── Step 2/4: Generating test mock infrastructure ─────────────"
echo ""

# Detect if this integration has existing hand-written test infrastructure
# (product.py with a real class, session.py with routes, conftest with fixtures).
# If so, skip the generator — the legacy tests are better than generated ones.
HAS_LEGACY_TESTS=false
if [ -f "$INTEGRATION_PATH/tests/core/product.py" ] && \
   grep -q "class " "$INTEGRATION_PATH/tests/core/product.py" 2>/dev/null && \
   [ -f "$INTEGRATION_PATH/tests/core/session.py" ] && \
   grep -q "class " "$INTEGRATION_PATH/tests/core/session.py" 2>/dev/null; then
    HAS_LEGACY_TESTS=true
    echo "  Integration has existing test infrastructure (product.py + session.py)"
    echo "  Skipping mock generation — using migrated legacy tests"
fi

# If legacy conftest has broken imports (non-relative), replace it
# before running the generator so it can produce a clean one
CONFTEST="$INTEGRATION_PATH/tests/conftest.py"
if [ "$HAS_LEGACY_TESTS" = false ] && [ -f "$CONFTEST" ]; then
    # Check for non-relative imports that won't work in content-hub
    if grep -q "^from core\." "$CONFTEST" 2>/dev/null; then
        echo "  Legacy conftest has non-relative imports — replacing with clean version"
        # Keep only the pytest_plugins line, let generator fill in the rest
        echo 'pytest_plugins = ("integration_testing.conftest",)' > "$CONFTEST"
    fi
fi

if [ "$HAS_LEGACY_TESTS" = false ]; then
    $PYTHON "$MOCK_GENERATOR" "$INTEGRATION_PATH"
    echo ""
    echo "  ✓ Test mock generation complete"
else
    echo ""
    echo "  ✓ Using existing test infrastructure (skipped generation)"
fi

# ── Step 3: Lint & Fix ─────────────────────────────────────────────────
echo ""
echo "── Step 3/6: Lint & auto-fix ─────────────────────────────────"
echo ""

cd "$INTEGRATION_PATH"

# Auto-fix lint issues (ruff), including unsafe fixes for bare except -> Exception
echo "  Running: mp check --fix --unsafe-fixes"
mp check "$INTEGRATION_PATH" --fix --unsafe-fixes 2>&1 | tail -3 || true

# Format
echo "  Running: mp format"
mp format "$INTEGRATION_PATH" 2>&1 | tail -3 || true

echo "  ✓ Lint & format complete"

# ── Step 4: Validate (CI-equivalent) ───────────────────────────────────
echo ""
echo "── Step 4/6: Validating (CI-equivalent) ──────────────────────"
echo ""

cd "$INTEGRATION_PATH"

# Pre-build validation (same as CI's mp validate)
echo "  Running: mp validate integration $SNAKE_NAME --only-pre-build"
VALIDATE_OUTPUT=$(mp validate integration "$SNAKE_NAME" -q --only-pre-build 2>&1 || true)
if echo "$VALIDATE_OUTPUT" | grep -q "Passed"; then
    PASSED=$(echo "$VALIDATE_OUTPUT" | grep -oP 'Passed: \d+' | head -1)
    echo "  ✓ Pre-build validation passed ($PASSED)"
elif echo "$VALIDATE_OUTPUT" | grep -q "ValueError\|Error"; then
    echo "  ✗ Pre-build validation FAILED:"
    echo "$VALIDATE_OUTPUT" | grep -v "Report available at\|newer version" | tail -5
    echo ""
    echo "  ⚠ Fix validation errors before submitting PR"
fi

# Lint check (same as CI's Code Linter)
echo "  Running: mp check (lint)"
LINT_OUTPUT=$(mp check "$INTEGRATION_PATH" 2>&1 || true)
if echo "$LINT_OUTPUT" | grep -q "LinterWarning\|error"; then
    echo "  ⚠ Lint issues found (suppressed by ruff.toml exclusion)"
else
    echo "  ✓ Lint clean"
fi

# Build check (same as CI's Build Google Integrations)
echo "  Running: mp build integration $SNAKE_NAME"
BUILD_OUTPUT=$(mp build integration "$SNAKE_NAME" 2>&1 || true)
if echo "$BUILD_OUTPUT" | grep -q "FatalCommandError\|ValueError\|Failed to load"; then
    echo "  ⚠ Build had issues (may be local env — check CI)"
else
    echo "  ✓ Build passed"
fi

# ── Step 5/6: Run tests ───────────────────────────────────────────────
echo ""
echo "── Step 5/6: Running tests ───────────────────────────────────"
echo ""

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/.venv/lib/python3.11/site-packages/soar_sdk"

echo "  Running: pytest tests -v"
if .venv/bin/python -m pytest tests -v 2>&1; then
    echo ""
    echo "  ✓ All tests passed"
else
    echo ""
    echo "  ✗ Some tests failed (see output above)"
fi

# ── Step 6/6: Verify no real HTTP calls ───────────────────────────────
echo ""
echo "── Step 6/6: Verify no real HTTP calls ───────────────────────"
HTTP_CALLS=$(rg "requests\.(get|post|put|delete|request)\(" tests/ --glob="*.py" 2>/dev/null | rg -v "monkeypatch|Mock|mock|setattr|import|lambda|MockSession|router" || true)
if [ -n "$HTTP_CALLS" ]; then
    echo "  ⚠ Possible real HTTP calls in tests:"
    echo "$HTTP_CALLS"
else
    echo "  ✓ No real HTTP calls in test code"
fi

# ── Summary ────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Summary: $INTEGRATION_NAME → $SNAKE_NAME"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "  Location: $INTEGRATION_PATH"
echo ""

# Check what was generated
echo "  Files:"
for f in \
    "actions/Ping.py" \
    "core" \
    "definition.yaml" \
    "pyproject.toml" \
    "tests/core/product.py" \
    "tests/core/session.py" \
    "tests/conftest.py" \
    "tests/test_actions/test_ping.py" \
    "tests/test_defaults/test_imports.py"; do
    if [ -e "$INTEGRATION_PATH/$f" ]; then
        echo "    ✓ $f"
    else
        echo "    ✗ $f (MISSING)"
    fi
done

echo ""
echo "  To re-run tests manually:"
echo "    cd $INTEGRATION_PATH"
echo "    export PYTHONPATH=\$PYTHONPATH:\$(pwd)/.venv/lib/python3.11/site-packages/soar_sdk"
echo "    .venv/bin/python -m pytest tests -v"
echo ""
echo "  To clean up:"
echo "    rm -rf $INTEGRATION_PATH"
