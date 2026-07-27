@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ======================
rem Config / defaults
rem ======================
set "VERBOSE=false"
set "QUIET=false"

rem ======================
rem Parse args
rem Supported flags: -v/--verbose, -q/--quiet
rem Everything else is treated as an integration path
rem ======================
set "INTEGRATIONS="
for %%A in (%*) do (
    if /I "%%~A"=="-v" (
        set "VERBOSE=true"
    ) else if /I "%%~A"=="--verbose" (
        set "VERBOSE=true"
    ) else if /I "%%~A"=="-q" (
        set "QUIET=true"
    ) else if /I "%%~A"=="--quiet" (
        set "QUIET=true"
    ) else (
        set "INTEGRATIONS=!INTEGRATIONS! "%%~A""
    )
)

call :main
exit /b %ERRORLEVEL%

:main
    call :init_echo
    call :print_info "[INFO] Starting..."
    set "OVERALL_STATUS=0"

    if not defined INTEGRATIONS (
        call :print_info "No integrations provided."
        exit /b 0
    )

    for %%I in (!INTEGRATIONS!) do (
        set "INTEGRATION=%%~I"
        for %%# in ("!INTEGRATION!") do set "INTEGRATION_NAME=%%~nx#"
        call :print_info "---------- Processing integration: !INTEGRATION_NAME!"
        call :test_integration "!INTEGRATION!"
        if errorlevel 1 (
            set "OVERALL_STATUS=!ERRORLEVEL!"
            call :log_error "Processing failed for integration '!INTEGRATION!' with status !OVERALL_STATUS!."
        ) else (
            call :log_debug "Integration '!INTEGRATION!' processed successfully."
        )
    )

    if "!OVERALL_STATUS!"=="0" (
        call :log_debug "All integrations processed successfully."
        call :print_info "[INFO] All operations completed successfully."
    ) else (
        call :print_info "[INFO] Operations failed. Final status: !OVERALL_STATUS!"
    )
    exit /b !OVERALL_STATUS!

:test_integration
    set "INTEG_PATH=%~1"
    set "ORIGINAL_PYTHONPATH=%PYTHONPATH%"
    if not exist "%INTEG_PATH%" (
        call :log_error "%INTEG_PATH% does not exist"
        exit /b 1
    )

    set "TESTS_DIR=%INTEG_PATH%\tests"
    if not exist "%TESTS_DIR%" (
        call :print_info "No tests directory found at %TESTS_DIR%."
        exit /b 0
    )

    call :log_debug "Integration tests path: %TESTS_DIR%"
    pushd "%INTEG_PATH%" || (call :log_error "Failed to cd to %INTEG_PATH%" & exit /b 1)

    set "VENV=.venv"
    call :sync_venv "%VENV%"
    if errorlevel 1 (
        set "RC=%ERRORLEVEL%"
        call :log_error "Failed to sync venv for %INTEG_PATH%. Status: %RC%"
        call :cleanup_and_exit
        exit /b %RC%
    )

    call :add_sdk_to_pythonpath "%VENV%"
    if errorlevel 1 (
        set "RC=%ERRORLEVEL%"
        call :cleanup_and_exit
        exit /b %RC%
    )

    call :source_venv "%VENV%"
    if errorlevel 1 (
        set "RC=%ERRORLEVEL%"
        call :log_error "Failed to activate venv for %INTEG_PATH%. Status: %RC%"
        call :cleanup_and_exit
        exit /b %RC%
    )

    call :log_debug "Running tests for integration %INTEG_PATH%"
    call :run_tests "%VENV%"
    set "TEST_RC=%ERRORLEVEL%"
    call :log_debug "Tests for %INTEG_PATH% finished with status %TEST_RC%."

    call :cleanup_and_exit
    exit /b %TEST_RC%


:sync_venv
    set "VENV=%~1"
    if exist "%VENV%" (
        call :log_debug "Virtual environment already exists in %CD%\%VENV%"
        exit /b 0
    )

    call :log_debug "Creating new virtual environment in %CD%\%VENV%"
    rem uv will create the venv (.venv) according to pyproject config by default
    if /I "%VERBOSE%"=="true" (
        call uv sync --dev --verbose
    ) else if /I "%QUIET%"=="true" (
        call uv sync --dev --quiet
    ) else (
        call uv sync --dev
    )
    if errorlevel 1 (
        set "RC=%ERRORLEVEL%"
        call :log_error "uv sync failed with status %RC% for %CD%\%VENV%"
        exit /b %RC%
    )
    exit /b 0

:source_venv
    set "VENV=%~1"
    set "ACT=%VENV%\Scripts\activate.bat"
    call :log_debug "Attempting to activate venv: %CD%\%ACT%"
    if not exist "%ACT%" (
        call :log_error "Activation script not found: %CD%\%ACT%"
        exit /b 1
    )
    call "%ACT%"
    exit /b 0

:add_sdk_to_pythonpath
    set "VENV=%~1"
    rem Use the venv's python to ask for site-packages
    set "VENV_PY=%VENV%\Scripts\python.exe"
    if not exist "%VENV_PY%" (
        call :log_error "Python not found in venv: %CD%\%VENV_PY%"
        exit /b 1
    )

    rem Ask Python for the primary site-packages path
    for /f "usebackq delims=" %%S in (`"%VENV_PY%" -c "import site,sys; print(next((p for p in site.getsitepackages()+[site.getusersitepackages()] if p.endswith('site-packages')), '' ))"`) do (
        set "SITE_PACKAGES=%%S"
    )

    if not defined SITE_PACKAGES (
        rem Fallback to Windows venv default layout
        set "SITE_PACKAGES=%CD%\%VENV%\Lib\site-packages"
    )

    set "SDK_DIR=%SITE_PACKAGES%\soar_sdk"
    if not exist "%SDK_DIR%" (
        call :log_debug "Can't find the SDK at the expected path: %SDK_DIR%"
        rem If SDK truly must be present, treat as error (aligns with .sh behavior)
        exit /b 1
    )

    rem Prepend to PYTHONPATH if not already included
    call :ensure_pythonpath "%SDK_DIR%"
    exit /b %ERRORLEVEL%

:ensure_pythonpath
    set "ADD=%~1"
    set "CURRENT=%PYTHONPATH%"
    rem Simple containment check (case-insensitive not guaranteed)
    echo;%CURRENT%; | find /I ";%ADD%;">nul
    if errorlevel 1 (
        if defined PYTHONPATH (
            set "PYTHONPATH=%ADD%;%PYTHONPATH%"
        ) else (
            set "PYTHONPATH=%ADD%"
        )
        call :log_debug "Added %ADD% to PYTHONPATH"
    ) else (
        call :log_debug "%ADD% already in PYTHONPATH"
    )
    exit /b 0

:run_tests
    set "VENV=%~1"
    set "VENV_PY=%VENV%\Scripts\python.exe"
    if not exist "%VENV_PY%" (
        call :log_error "Python not found in venv: %CD%\%VENV_PY%"
        exit /b 1
    )
    if /I "%VERBOSE%"=="true" (
        "%VENV_PY%" -m pytest --json-report --json-report-file=.report.json -vv .\tests
    ) else if /I "%QUIET%"=="true" (
        "%VENV_PY%" -m pytest --json-report --json-report-file=.report.json -qq .\tests
    ) else (
        "%VENV_PY%" -m pytest --json-report --json-report-file=.report.json .\tests
    )
    exit /b %ERRORLEVEL%

:cleanup_and_exit
    call :deactivate_venv
    set "PYTHONPATH=%ORIGINAL_PYTHONPATH%"
    popd
    exit /b

:deactivate_venv
    if defined VIRTUAL_ENV (
        call :log_debug "Deactivating venv"
        call deactivate >nul 2>&1
    )
    exit /b 0

rem ======================
rem Logging helpers
rem ======================
:init_echo
    rem We’ll keep output plain (no ANSI), to avoid \U/\u escape pitfalls.
    rem Windows 10+ supports ANSI, but CMD/legacy consoles can be inconsistent.
    goto :eof

:print_info
    rem %~1 is the full message (already bracketed if needed)
    echo %~1
    goto :eof

:log_error
    >&2 echo [ERROR] %~1
    goto :eof

:log_debug
    if /I "%VERBOSE%"=="true" (
        echo [DEBUG] %~1
    )
    goto :eof
