import json
import sys
import os
import click
import subprocess
from utils.helper import check_path_type,resolve_path, run_command, parse_size_to_string


@click.group()
def module():
    """
    Filesystem analysis module.
    """
    pass


@module.command()
@click.argument('dir_path', type=click.Path())
@click.option("--depth", type=click.INT, default=0, help="Maximum depth of recursion. Default 0.")
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


@module.command()
@click.argument("file_path", type=click.Path())
@click.argument("mount_path", type=click.Path())
@click.pass_context
def mount_disk(ctx, file_path, mount_path):
    """
    Mount a disk image in read-only mode.

    FILE_PATH is the path to the disk image.
    MOUNT_PATH is the directory where the image will be mounted.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)

        # check_path_type(ctx.obj['workdir'], mount_path, has_to_be_file=False)
        mount_path = resolve_path(ctx.obj['workdir'], mount_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        _mount_disk_image(file_path, mount_path)
    except Exception as e:
        click.echo(f"Error: {e}")


@module.command()
@click.argument("mount_path", type=click.Path())
@click.pass_context
def unmount_disk(ctx,mount_path):
    """
    Unmount a mounted disk image.

    MOUNT_PATH is the directory where the image is mounted.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], mount_path, has_to_be_file=False)
        mount_path = resolve_path(ctx.obj['workdir'], mount_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        _unmount_disk_image(mount_path)
    except Exception as e:
        click.echo(f"Error: {e}")

#-------------help functions-------------

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

# todo need to fix bug, not there is problem with mounting disk with partitions
def _mount_disk_image(file_path, mount_path):
    """
        Mount a disk image in read-only mode using a loop device.

        :param file_path: Path to the disk image file.
        :param mount_path: Path to the directory where the image will be mounted.
        :raises Exception: If the mounting process fails.
        """
    try:
        # Ensure the mount point exists or create it
        if not os.path.exists(mount_path):
            subprocess.run(["sudo", "mkdir", mount_path], check=True)

        if len(os.listdir(mount_path)) != 0:
            raise Exception(f"Dir is not empty: {mount_path}")

        # Mount the disk image in read-only mode
        command = ["sudo", "mount", "-o", "ro,loop,noexec", file_path, mount_path]
        subprocess.run(command, check=True)
        click.echo(f"Disk image {file_path} successfully mounted at {mount_path} in read-only mode.")

    except subprocess.CalledProcessError as e:
        raise Exception(f"Error mounting the disk image: {e.stderr.strip()}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")

def _unmount_disk_image(mount_path):
    """
        Unmount a mounted disk image.

        :param mount_path: Path to the directory where the image is mounted.
        :raises Exception: If the unmounting process fails.
        """
    try:
        # Unmount the disk image
        command = ["sudo", "umount", mount_path]
        subprocess.run(command, check=True)
        subprocess.run(["sudo", "rm","-r", mount_path], check=True)
        click.echo(f"Disk image successfully unmounted from {mount_path}.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error unmounting the disk image: {e.stderr.strip()}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")