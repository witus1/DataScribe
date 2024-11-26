import subprocess
import os

def run_command(command):
    """Run a shell command and return the output."""
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {result.stderr}")
    return result.stdout.strip()

def resolve_path(path, ctx_path):
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
