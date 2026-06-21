import click
from .scanner import find_used_variables, read_env_file


@click.command("scan-env")
@click.argument("project_path", default=".")
@click.option("--env-file", default=".env")
@click.option("--example-file", default=".env.example")
def env_scan_command(project_path, env_file, example_file):
    used = find_used_variables(project_path)
    env_vars = read_env_file(env_file)
    example_vars = read_env_file(example_file)

    unused = env_vars - used
    missing = used - example_vars

    for var in sorted(used):
        click.echo(f"✓ {var} is used")

    for var in sorted(unused):
        click.echo(f"⚠ {var} appears unused")

    for var in sorted(missing):
        click.echo(f"✗ {var} used in code but missing from .env.example")