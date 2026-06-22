from pathlib import Path
import click
from .scanner import find_used_variables, read_env_file


@click.command("scan-env")
@click.argument("project_path", default=".")
@click.option("--env-file", default=".env")
@click.option("--example-file", default=".env.example")
def env_scan_command(project_path, env_file, example_file):
    used = find_used_variables(project_path)

    project_root = Path(project_path)

    env_path = Path(env_file)
    if not env_path.is_absolute():
        env_path = project_root / env_path

    example_path = Path(example_file)
    if not example_path.is_absolute():
        example_path = project_root / example_path

    env_vars = read_env_file(str(env_path))
    example_vars = read_env_file(str(example_path))

    unused = env_vars - used
    missing = used - example_vars

    for var in sorted(used):
        click.echo(f"✓ {var} is used")

    for var in sorted(unused):
        click.echo(f"⚠ {var} appears unused")

    for var in sorted(missing):
        click.echo(f"✗ {var} used in code but missing from .env.example")