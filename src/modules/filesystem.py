import json
import sys
import os
import click
from utils.helper import check_path_type,resolve_path, run_command, parse_size_to_string


@click.group()
def module():
    """
    Filesystem analysis module.
    """
    pass


@module.command()
@click.argument('dir_path', type=click.Path())
@click.option("--depth", type=click.INT, default=0, help="Maximum depth of recursion.")
@click.option("--include-files", is_flag=True, default=False, help="Include files by listing.")
@click.pass_context
def directory_size(ctx, dir_path, depth, include_files):
    """
        Calculate the total size of a directory and list sizes of subdirectories/files.

        DIR_PATH is the path to the directory to calculate the size of.
    """

    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], dir_path, has_to_be_file=False)
        dir_path = resolve_path(ctx.obj['workdir'], dir_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        entries = _list_directory_sizes(dir_path, depth, include_files)

        click.echo(f"Directory size summary for '{dir_path}':")
        for path, size in entries:
            if isinstance(size, int):  # Valid size
                size_str = parse_size_to_string(size)
                click.echo(f"- {path}: {size_str}")
            else:  # Error case
                click.echo(f"- {path}: {size}")
    except Exception as e:
        click.echo(f"Error: {e}")


def _list_directory_sizes(dir_path, depth, include_files):
    """
    List the sizes of subdirectories and files in a directory, up to a given depth.

    :param dir_path: Path to the directory.
    :param depth: Maximum depth to traverse (0 for current directory only).
    :param include_files: Whether to include file sizes in the output.
    :return: A list of tuples (path, size_in_bytes).
    """
    entries = []
    try:
        if os.path.isdir(dir_path):

            result = run_command(["du", "--bytes", "--max-depth", str(depth), dir_path])
            # Parse the output to: <size> <path>
            for line in result.splitlines():
                size, path = line.split("\t")
                entries.append((path, int(size)))

        # Include individual file sizes if requested
        if include_files:
            for root, _, files in os.walk(dir_path):
                current_depth = root[len(dir_path):].count(os.sep)
                if current_depth >= depth:
                    break

                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = int(run_command(["stat", "-c", "%s", file_path]))
                        entries.append((file_path, file_size))
                    except Exception as e:
                        entries.append((file_path, f"Error: {e}"))
    except Exception as e:
        raise Exception(f"Error listing directory sizes for {dir_path}: {e}")

    return entries
