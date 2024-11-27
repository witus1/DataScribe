import subprocess
import os
import click

def run_command(command):
    """Run a shell command and return the output."""
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {result.stderr}")
    return result.stdout.strip()

def resolve_path(ctx_path, path):
    """
    Resolve a given path relative to the current working directory.

    :param path: The input path to resolve.
    :param ctx_path: The current working directory to resolve relative paths.
    :return: An absolute path after resolving.
    """
    if os.path.isabs(path):
        # If the path is absolute, return it as-is
        return os.path.abspath(path)
    else:
        # Otherwise, resolve it relative to the current working directory
        return os.path.abspath(os.path.join(ctx_path, path))

def check_path_type(ctx_path, path, has_to_be_file):
    """
        Determine if the given path is a file or a directory after resolving it.
        :param ctx_path: Context of the current working directory .
        :param path: Path to check.
        :param has_to_be_file: Boolean to determine if the path is a file or a directory.
        :raises BadParameter: If the path of certain type is invalid.
    """
    resolved_path = resolve_path(ctx_path, path)

    if not os.path.exists(resolved_path):
        raise click.BadParameter(f"Invalid path: {resolved_path}")

    if not has_to_be_file and os.path.isfile(resolved_path):
        raise click.BadParameter(f"Given path is not a directory: {resolved_path}")

    elif has_to_be_file and os.path.isdir(resolved_path):
        raise click.BadParameter(f"Given path is not a file: {resolved_path}")
