import click
import os
from utils.config import set_working_directory, get_working_directory, save_config
from utils.helper import resolve_path
from modules import metadata, filesystem, multimedia, log_extraction
import utils.tools_availability as ta
import subprocess

@click.group(invoke_without_command=True)
@click.option("--get-workdir", is_flag=True, help="Print the current working directory.")
@click.option("--set-workdir", type=click.Path(), help="Set the working directory.")
@click.pass_context
def cli(ctx, get_workdir, set_workdir):
    """
    DataScribe CLI - Modular forensic analysis tool.
    """
    # Load the working directory into the context
    ctx.ensure_object(dict)  # Ensure ctx.obj exists
    ctx.obj["workdir"] = get_working_directory()

    if get_workdir:
        # Print the current working directory
        click.echo(f"Current working directory: {ctx.obj['workdir']}")
        ctx.exit(0)

    if set_workdir:
        # Resolve the path using the helper function
        resolved_path = resolve_path(ctx.obj["workdir"],set_workdir)
        try:
            if os.path.exists(resolved_path) and os.path.isdir(resolved_path):
                save_config({"workdir": resolved_path})
                click.echo(f"Working directory set to: {resolved_path}")
            else:
                raise ValueError(f"Invalid directory: \033[91m{resolved_path}\033[0m")
        except ValueError as e:
            click.echo(str(e))
        ctx.exit(0)
    # If no options or commands are provided, print help
    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


@cli.command()
@click.option("-i", "--install", is_flag=True, help="Install missing tools.")
def check_tools(install):
    """
    Check availability of required Linux tools and optionally install missing tools.
    """
    missing_tools = ta.check_tool_availability()
    if missing_tools:
        click.echo("Missing tools found.")
        for tool in missing_tools:
            click.echo(tool)
        if install:
            instalation_message = ta.install_missing_tools(missing_tools)
            click.echo(instalation_message)
    else:
        click.echo("No missing tools found.")
# Dynamically register module commands
cli.add_command(filesystem.module, name="filesystem")
cli.add_command(metadata.module, name="metadata")
cli.add_command(multimedia.module, name="multimedia")
cli.add_command(log_extraction.module, name="log-extraction")

if __name__ == "__main__":
    cli()