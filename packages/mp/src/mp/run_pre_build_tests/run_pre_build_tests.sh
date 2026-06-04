#!/bin/bash

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# shellcheck disable=SC3030
# shellcheck disable=SC3043

VERBOSE=false
QUIET=false
INTEGRATIONS=()

main() {
  init_args "${@}"
  test_integrations
  local final_status=$?
  if [ ${final_status} -eq 0 ]; then
    print_with_color "[INFO] All operations completed successfully."
  else
    print_with_color "[INFO] Operations failed. Final status: ${final_status}"
  fi
  exit ${final_status}
}

test_integrations() {
  local overall_status=0
  for integration in "${INTEGRATIONS[@]}"; do
    integration_name=$(basename "${integration}")
    print_with_color "---------- Processing integration: ${integration_name}"
    test_integration "${integration}"
    local integration_status=$?
    if [ ${integration_status} -ne 0 ]; then
      log_error "Processing failed for integration '${integration}' with status ${integration_status}."
      overall_status=${integration_status}
    else
      log_debug "Integration '${integration}' processed successfully."
    fi
  done

  if [ ${overall_status} -eq 0 ]; then
    log_debug "All integrations processed successfully."
  fi
  return ${overall_status}
}

test_integration() {
  integration_path="$1"
  validate_directory "${integration_path}"

  integration_tests_path="${integration_path}/tests"
  if [ -d "${integration_tests_path}" ]; then
    log_debug "Integration tests path: ${integration_tests_path}"

    local original_dir
    original_dir=$(pwd)
    if ! cd "${integration_path}"; then
      log_error "Failed to cd to ${integration_path}"
      return 1
    fi

    local venv_path=".venv"

    sync_venv "${venv_path}"
    local sync_status=$?
    if [ ${sync_status} -ne 0 ]; then
      log_error "Failed to sync venv for ${integration_path}. Status: ${sync_status}"
      if ! cd "${original_dir}"; then
        log_error "Critical: Failed to cd back to ${original_dir}."
        exit 1
      fi
      return ${sync_status}
    fi

    add_sdk_to_python_path "${venv_path}"

    source_venv "${venv_path}"
    local source_status=$?
    if [ ${source_status} -ne 0 ]; then
      log_error "Failed to source venv for ${integration_path}. Status: ${source_status}"
      if ! cd "${original_dir}"; then
        log_error "Critical: Failed to cd back to ${original_dir}."
        exit 1
      fi
      return ${source_status}
    fi

    log_debug "Running tests for integration ${integration_path}"
    run_tests "${venv_path}"
    local test_status=$?
    log_debug "Tests for ${integration_path} finished with status ${test_status}."

    if ! cd "${original_dir}"; then
      log_error "Critical: Failed to cd back to ${original_dir} from $(pwd). Exiting."
      exit 1
    fi

    return ${test_status}
  else
    print_with_color "No tests directory found at ${integration_tests_path}."
    return 0
  fi
}

validate_directory() {
  path="$1"
  if [ ! -d "${path}" ]; then
    log_error "${path} does not exist"
    exit 1
  fi
}

add_sdk_to_python_path() {
  venv_path="$1"
  python_version=$(python3 -V 2>&1 | awk '{print $2}' | cut -d'.' -f1,2)
  sdk_path="$(pwd)/${venv_path}/lib/python${python_version}/site-packages/soar_sdk"
  if [ ! -d "${sdk_path}" ]; then
    base=$(pwd)/${venv_path}
    for dir in "${base}"/lib/*; do
      sdk_path="${dir}/site-packages/soar_sdk"
      if [ -d "${sdk_path}" ]; then
        break
      fi
    done

    if [ ! -d "${sdk_path}" ]; then
      log_debug "Can't find the SDK at the expected path: ${sdk_path}"
      exit 1
    fi
  fi

  add_path_to_pyhon_path "${sdk_path}"
  trap 'remove_path_python_path "${sdk_path}"' EXIT INT
}

add_path_to_pyhon_path() {
  for path in "${@}"; do
    if [[ ":PYTHONPATH:" != *"${path}"* ]]; then
      log_debug "Adding ${path} to PYTHONPATH"
      PYTHONPATH="${path}:${PYTHONPATH}"
      export PYTHONPATH
    else
      log_debug "${path} already added to PYTHONPATH"
    fi
  done
}

remove_path_python_path() {
  path="$1"
  log_debug "Removing ${path} from PYTHONPATH"
  PYTHONPATH=$(echo "$PYTHONPATH" | sed -e "s|${path}:||" -e "s|:${path}||" -e "s|${path}||")
  export PYTHONPATH
}

sync_venv() {
  venv_path="$1"
  if [ -d "${venv_path}" ]; then
    log_debug "Virtual environment already exists in $(pwd)/${venv_path}"
  else
    log_debug "Creating new virtual environment in $(pwd)/${venv_path}"
    local sync_cmd_output
    local sync_status
    if [ "${VERBOSE}" = true ]; then
      sync_cmd_output=$(uv sync --dev --verbose 2>&1)
      sync_status=$?
    elif [ "${QUIET}" = true ]; then
      sync_cmd_output=$(uv sync --dev --quiet 2>&1)
      sync_status=$?
    else
      sync_cmd_output=$(uv sync --dev 2>&1)
      sync_status=$?
    fi

    if [ ${sync_status} -ne 0 ]; then
      log_error "uv sync failed with status ${sync_status} for $(pwd)/${venv_path}"
      if [ -n "${sync_cmd_output}" ]; then log_error "uv sync output: ${sync_cmd_output}"; fi
      return ${sync_status}
    else
      if [ "${VERBOSE}" = true ] && [ -n "${sync_cmd_output}" ]; then log_debug "uv sync output: ${sync_cmd_output}"; fi
    fi
  fi
  return 0
}

source_venv() {
  venv_path="$1"
  venv_activate_script="${venv_path}/bin/activate"
  log_debug "Attempting to source venv: $(pwd)/${venv_activate_script}"
  if [ -f "${venv_activate_script}" ]; then
    # shellcheck source="${venv_path}/bin/activate"
    . "${venv_activate_script}"
    trap 'deactivate_venv' EXIT INT
    return 0
  else
    log_error "Activation script not found: $(pwd)/${venv_activate_script}"
    return 1
  fi
}

deactivate_venv() {
  if type deactivate >/dev/null 2>&1; then
    log_debug "Deactivating venv"
    deactivate
  fi
}

run_tests() {
  venv_path="$1"
  if [ "${VERBOSE}" = true ]; then
    "${venv_path}/bin/python3" -m pytest --json-report --json-report-file=.report.json -vv ./tests
  elif [ "${QUIET}" = true ]; then
    "${venv_path}/bin/python3" -m pytest --json-report --json-report-file=.report.json -qq ./tests
  else
    "${venv_path}/bin/python3" -m pytest --json-report --json-report-file=.report.json ./tests
  fi
}

print_with_color() {
  printf "%b\n" "$1"
}

log_error() {
  print_with_color "[ERROR] $1" >&2
}

log_debug() {
  if [ "${VERBOSE}" = true ]; then
    print_with_color "[DEBUG] $1"
  fi
}

init_args() {
  while [ ${#} -gt 0 ]; do
    case "$1" in
    -v | --verbose)
      VERBOSE=true
      shift
      ;;
    -q | --quiet)
      QUIET=true
      shift
      ;;
    *)
      INTEGRATIONS+=("$1")
      shift
      ;;
    esac
  done
}

main "${@}"