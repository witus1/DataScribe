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


def parse_size_from_string(size_str):
    """
    Parse a human-readable size string (e.g., '64 MB', '24,5 MB') into bytes.
    :param size_str: Size string to parse.
    :return: Size in bytes as an integer.
    """
    units ={
        "tb": 1024 ** 4,
        "gb": 1024 ** 3,
        "mb": 1024 ** 2,
        "kb": 1024,
        "b": 1
    }

    size_str = size_str.strip().lower().replace(",", ".")  # Normalize input
    for unit in units:
        if size_str.endswith(unit):
            try:
                # Remove the unit from the string and convert to a float
                numeric_part = size_str.removesuffix(unit)
                value = float(numeric_part)
                return int(value * units[unit])
            except ValueError:
                raise ValueError(f"Invalid size value: {size_str}")
    raise ValueError(f"Unknown size unit in: {size_str}")


def parse_size_to_string(size_bytes):
    """
        Convert size in bytes to a human-readable format.
        :param size_bytes: Size in bytes.
        :return: Formatted size string (e.g., '100 MB', '1.5 GB').
        """
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"
