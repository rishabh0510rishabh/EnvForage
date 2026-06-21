# Script Safety Policy

Because EnvForage generates executable shell (`.sh`) and PowerShell (`.ps1`) scripts that run on real hardware, script safety is our highest priority. 

This document defines the strict boundaries of what our scripts are allowed to do.

## 1. Prohibited Commands (The "Never" List)

EnvForage scripts will **never** include or generate the following commands. These are actively blocked by the `SafetyFilter` in the Template Engine:

- **Delete system files**: No recursive deletions of the root directory (`rm -rf /`) or user home directories (`rm -rf ~`). The safety regex uses a negative lookahead (`(?!\w)`) to allow standard Docker cleanup patterns like `rm -rf /var/lib/apt/lists/*`. See [ADR-008](./decisions/ADR-008-safety-filter-negative-lookahead.md).
- **Modify boot configs**: No modifications to GRUB, Windows Boot Manager, or kernel parameters.
- **Uninstall drivers automatically**: Scripts will not run `apt-get purge nvidia-*` or similar commands. If a driver update is required, the script will halt and instruct the user to perform the update manually.
- **Filesystem Formatting**: Commands like `mkfs` or `format` are strictly blocked.
- **Raw Disk Writes**: Commands like `dd` to raw disk partitions are blocked.
- **Unsafe Network Execution**: Piping web content directly to a shell (`curl | bash`) is prohibited.
- **Database Drops**: `DROP TABLE` or `DROP DATABASE` commands are blocked.

## 2. Allowed Automation Scope

EnvForage scripts are scoped to *user-space ML environment provisioning*.

**Allowed actions include:**
- Creating and activating Python virtual environments (`venv`, `conda`).
- Installing Python packages via `pip`.
- Installing system dependencies via package managers (`apt`, `winget`) *provided they do not conflict with core OS graphics drivers*.
- Downloading pre-trained model weights to specific project directories.
- Setting environment variables locally (e.g., `LD_LIBRARY_PATH`, `CUDA_HOME`).

## 3. Safety Checks (Pre-Flight)

Every EnvForage `setup.sh` or `setup.ps1` script must include pre-flight checks before making any changes.

**Required Checks:**
1. **OS Check**: Verify the current OS matches the script's intended target.
2. **Python Check**: Verify the required Python base version is available.
3. **CUDA Check**: If the profile requires CUDA, verify `nvcc` or `nvidia-smi` is reachable before attempting to install CUDA-dependent packages (like `torch+cu121`).

If a pre-flight check fails, the script must `exit 1` immediately with a clear, readable error message.

## 4. Rollback Philosophy

Currently, shell scripts do not have native transactional rollbacks. To mitigate this:
- **Isolation**: We strongly prefer creating isolated Virtual Environments (`.venv`) rather than installing packages globally. Deleting a failed environment is as simple as `rm -rf .venv`.
- **Containerization**: For absolute safety and guaranteed rollback, users are encouraged to use the `Dockerfile` output format rather than running scripts directly on the host OS.
