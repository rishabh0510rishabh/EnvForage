"""CLI utility to validate EnvForge profile configurations against schemas and logic rules."""
import os
import sys
from pathlib import Path

import click
import yaml
from pydantic import ValidationError

# Add backend directory to sys.path to allow importing app module
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.seed_profile import ProfileSeedSchema, ProfilesYamlSchema


def validate_logical_consistency(profile: ProfileSeedSchema) -> list[str]:
    """Perform logical consistency checks on a profile schema."""
    errors = []

    # 1. CUDA consistency: If cuda_required is True, cuda_versions must not be empty
    if profile.cuda_required and not profile.cuda_versions:
        errors.append("cuda_required is True, but cuda_versions is empty or not provided.")

    # 2. Unique packages: package names must be unique within a profile
    package_names = [pkg.name for pkg in profile.packages]
    duplicate_packages = {name for name in package_names if package_names.count(name) > 1}
    if duplicate_packages:
        errors.append(f"Duplicate package names found: {sorted(list(duplicate_packages))}.")

    # 3. Unique install orders: install_order values must be unique
    install_orders = [pkg.install_order for pkg in profile.packages]
    duplicate_orders = {order for order in install_orders if install_orders.count(order) > 1}
    if duplicate_orders:
        errors.append(f"Duplicate install_order values found: {sorted(list(duplicate_orders))}.")

    # 4. CUDA variant match: package cuda_variant must match one of the profile's cuda_versions
    for pkg in profile.packages:
        if pkg.cuda_variant:
            cv = pkg.cuda_variant
            # Convert cu118 -> 11.8, cu121 -> 12.1, etc.
            if cv.startswith("cu") and len(cv) >= 4 and cv[2:].isdigit():
                major = cv[2:-1]
                minor = cv[-1]
                mapped_ver = f"{major}.{minor}"
            else:
                mapped_ver = cv

            if not profile.cuda_versions or mapped_ver not in profile.cuda_versions:
                errors.append(
                    f"Package '{pkg.name}' specifies cuda_variant '{pkg.cuda_variant}' (mapped to '{mapped_ver}'), "
                    f"which is not compatible with profile cuda_versions: {profile.cuda_versions or []}."
                )

    return errors


def format_pydantic_error(exc: ValidationError) -> list[str]:
    """Format Pydantic ValidationError into human-readable messages."""
    formatted = []
    for error in exc.errors():
        loc_path = " -> ".join(str(p) for p in error["loc"])
        msg = error["msg"]
        formatted.append(f"  [{loc_path}]: {msg}")
    return formatted


def validate_profile_file(file_path: Path) -> tuple[bool, list[str]]:
    """Validate a single profile YAML file. Returns (is_valid, error_messages)."""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, UnicodeDecodeError) as e:
        return False, [f"Failed to read file: {e}"]
    except yaml.YAMLError as e:
        return False, [f"YAML Syntax Error: {e}"]

    if data is None:
        return True, ["File is empty (skipped)"]

    if not isinstance(data, dict):
        # Top level must be a dict
        return False, [f"Invalid YAML structure: expected a mapping at the root, got {type(data).__name__}."]

    # If the file does not have the 'profiles' key and lacks indicators of a single profile
    if "profiles" not in data and "os_support" not in data and "python_versions" not in data:
        return True, ["Not a profile file (skipped)"]

    # Determine schema type: list of profiles or single profile
    errors = []
    validated_profiles: list[ProfileSeedSchema] = []

    if "profiles" in data:
        try:
            yaml_schema = ProfilesYamlSchema.model_validate(data)
            validated_profiles = yaml_schema.profiles
        except ValidationError as e:
            errors.extend(format_pydantic_error(e))
    else:
        try:
            profile_schema = ProfileSeedSchema.model_validate(data)
            validated_profiles = [profile_schema]
        except ValidationError as e:
            errors.extend(format_pydantic_error(e))

    if errors:
        return False, errors

    # Logical consistency checks
    for idx, profile in enumerate(validated_profiles):
        logical_errors = validate_logical_consistency(profile)
        if logical_errors:
            prefix = f"Profile '{profile.slug}' " if len(validated_profiles) > 1 else ""
            for err in logical_errors:
                errors.append(f"  {prefix}Logical Error: {err}")

    if errors:
        return False, errors

    return True, []


@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
def main(path: Path) -> None:
    """Validate EnvForge profile YAML schemas and logical consistency rules."""
    files_to_validate: list[Path] = []

    if path.is_file():
        files_to_validate.append(path)
    elif path.is_dir():
        # Scan for yaml/yml files
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith((".yaml", ".yml")):
                    files_to_validate.append(Path(root) / file)

    if not files_to_validate:
        click.secho("No YAML files found to validate.", fg="yellow")
        sys.exit(0)

    total_files = len(files_to_validate)
    click.echo(f"Validating {total_files} file(s)...")

    failed_files = 0
    for file in sorted(files_to_validate):
        # Display relative path for clean logs
        rel_path = file.relative_to(backend_dir.parent) if backend_dir.parent in file.parents else file
        click.echo(f"Checking {rel_path}... ", nl=False)

        is_valid, errors = validate_profile_file(file)
        if is_valid:
            if errors and "skipped" in errors[0]:
                click.secho("SKIPPED (not a profile)", fg="yellow")
            else:
                click.secho("PASSED", fg="green")
        else:
            click.secho("FAILED", fg="red")
            failed_files += 1
            for err in errors:
                click.secho(err, fg="yellow")

    if failed_files > 0:
        click.secho(f"\nValidation failed: {failed_files}/{total_files} file(s) failed validation.", fg="red", bold=True)
        sys.exit(1)
    else:
        click.secho(f"\nValidation succeeded: All {total_files} file(s) passed validation.", fg="green", bold=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
