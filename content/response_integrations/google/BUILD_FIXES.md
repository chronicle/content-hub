# Build Fixes - Google Repository

This document tracks build failures for individual integrations and their corresponding fixes.

## Summary of Known Issues

| Integration | Error | Resolution / Status |
| :--- | :--- | :--- |
| **SiemplifyThreatFuse** | `FatalCommandError: Failed to download a binary wheel for 'numpy==2.4.4'.` | Proposed: Pin `numpy==2.1.3` in `pyproject.toml`. |
| **AnomaliThreatStream** | `FatalCommandError: Failed to download a binary wheel for 'numpy==2.4.4'.` | Proposed: Pin `numpy==2.1.3` in `pyproject.toml`. |
| **MalwareDomainList** | `FatalCommandError: Failed to download a binary wheel for 'numpy==2.4.4'.` | Proposed: Pin `numpy==2.1.3` in `pyproject.toml`. |

| **v_sphere** | `FatalCommandError: Failed to download a binary wheel for 'pyvmomi==8.0.2.0.1'.` | Fixed: Pinned `pyvmomi==9.0.0.0` in `pyproject.toml` (has binary wheels). |
| **bmc_helix_remedy_force** | `ValueError: Invalid image format. Expected PNG but found JPEG` | Fixed: Converted `resources/image.png` from JPEG to PNG using `sips`. |
| **salesforce** | `FatalCommandError: Failed to download a binary wheel for 'pypika==0.48.9'.` | Fixed: Pinned `pypika==0.51.1` in `pyproject.toml` (has binary wheels). |
| **sccm** | `FatalCommandError: Failed to download a binary wheel for 'future==0.18.3'.` | **Pending**: `wmi-client-wrapper-py3` requires `0.18.3` (no wheel). |

---

## Detailed Fixes

### salesforce
- **Issue**: Missing binary wheel for `pypika==0.48.9`.
- **Fix**: Upgraded to `pypika==0.51.1` which provides wheels on PyPI.
- **Status**: Fixed and validated.

### v_sphere
- **Issue**: Missing binary wheel for `pyvmomi==8.0.2.0.1`.
- **Fix**: Upgraded to `pyvmomi==9.0.0.0` which provides wheels on PyPI.
- **Status**: Fixed and validated.

### bmc_helix_remedy_force
- **Issue**: The asset `resources/image.png` was actually a JPEG file with a `.png` extension, causing a validation failure in `mp build`.
- **Fix**: Used `sips` to convert the file to true PNG format.
- **Status**: Fixed and validated.

### SiemplifyThreatFuse
- **Issue**: The build system requires binary wheels (`--only-binary=:all:`) for all dependencies. `numpy==2.4.4` was recently released and may not have a compatible binary wheel for the `manylinux` platforms targeted by the `mp build` process in this environment.
- **Root Cause**: `pandas==2.2.2` depends on `numpy`, and `uv` resolved it to the latest available version (`2.4.4`), which lacks the required wheels.
- **Fix**: Explicitly pin `numpy` to a stable version with wide wheel support (e.g., `2.1.3`) in the `dependencies` section of `pyproject.toml`.
- **Status**: Pending implementation and validation.

### AnomaliThreatStream
- **Issue**: Same as SiemplifyThreatFuse.
- **Fix**: Add `numpy==2.1.3` to `dependencies` in `pyproject.toml`.
- **Status**: Pending implementation and validation.

### MalwareDomainList
- **Issue**: Same as SiemplifyThreatFuse.
- **Fix**: Add `numpy==2.1.3` to `dependencies` in `pyproject.toml`.
- **Status**: Pending implementation and validation.
