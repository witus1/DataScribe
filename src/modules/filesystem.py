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


@module.command()
@click.argument("file_path", type=click.Path())
@click.option(
    "--tool",
    type=click.Choice(["fdisk", "parted", "file", "disktype","ewfinfo", "all"], case_sensitive=False),
    default="all",
    help=(
        "Specify the tool to use:\n"
        "- fdisk: Displays the partition table of the disk image.\n"
        "- parted: Displays detailed partition information.\n"
        "- file: Displays the file type of the disk image.\n"
        "- disktype: Displays detailed disk analysis, including filesystems and labels.\n"
        "- ewfinfo: Displays detailed disk information from E01 format. \n"
        "- all: Runs all tools (default)."
    ))
@click.pass_context
def disk_image_info(ctx, file_path, tool):
    """
    Analyze a disk image using various Linux tools.

    FILE_PATH is the path to the disk image file.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
    except Exception as e:
        click.echo(e)
        sys.exit()


    tools = ["fdisk", "parted", "file", "disktype","ewfinfo"] if tool == "all" else [tool]


    try:
        for t in tools:
            output = _run_disk_tool(t, file_path)
            click.echo(f"\n{t.upper()} Output:\n{'=' * 40}\n{output}\n")
    except Exception as e:
        click.echo(f"Error: {e}")


@module.command()
@click.argument("output_file_name", type=click.Path())
@click.argument("input_files",nargs=-1 ,type=click.Path())
@click.pass_context
def ewfexport(ctx,output_file_name, input_files):
    """
        Convert an EWF (E01) disk image to a raw disk image.

        INPUT_FILES is the path to the EWF disk image.
        OUTPUT_FILE_NAME is the path where the raw disk image will be saved. It should be the path to file without extension.
    """

    try:
        # Ensure at least one input file is provided
        if not input_files:
            raise Exception("No input files provided. Please specify at least one EWF file.")

        # check_path_type(ctx.obj['workdir'], output_file_name, has_to_be_file=False)
        output_file_name = resolve_path(ctx.obj['workdir'], output_file_name)

        if output_file_name == ctx.obj['workdir']:
            raise Exception("Output file name cannot be the same as the working directory.")

        # Validate and resolve each input file
        resolved_input_files = []
        for file_path in input_files:
            # Validate input paths
            check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
            resolved_path = resolve_path(ctx.obj['workdir'], file_path)
            resolved_input_files.append(resolved_path)

        # Perform the conversion
        _export_ewf_to_raw(resolved_input_files, output_file_name)
    except Exception as e:
        click.echo(e)
        sys.exit()
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
            subprocess.run(["sudo", "mkdir","-p", mount_path], check=True)

        if len(os.listdir(mount_path)) != 0:
            raise Exception(f"Dir is not empty: {mount_path}")

        # Mount the disk image in read-only mode

        loop_device = _setup_loop_device(file_path)
        partitions = _get_partition_info(loop_device)
        try:
            click.echo("Available partitions:")
            for idx, partition in enumerate(partitions, start=1):
                click.echo(f"{idx}: {partition}")
            choice = click.prompt("Choose a partition to mount", type=int, default=1)
            _mount_partition(partitions[choice - 1], mount_path)
        except:
            command = ["sudo", "mount", "-o", "ro,noexec", loop_device, mount_path]
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


def _run_disk_tool(tool, file_path):
    """
    Run a disk analysis tool on a given image file.

    :param tool: The tool to run (e.g., 'fdisk', 'parted', 'mmls', 'file', 'disktype').
    :param file_path: The path to the disk image file.
    :return: The output of the tool.
    :raises Exception: If the tool fails or is not found.
    """
    try:
        # Define the commands for each tool
        commands = {
            "fdisk": ["fdisk", "-l", file_path],
            "parted": ["parted", file_path, "print"],
            "file": ["file", file_path],
            "disktype": ["disktype", file_path],
            "ewfinfo": ["ewfinfo", file_path],
        }

        if tool not in commands:
            raise ValueError(f"Unsupported tool: {tool}")

        return run_command(commands[tool])
    except FileNotFoundError:
        raise Exception(f"Tool '{tool}' is not installed or not in the PATH.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error running '{tool}': {e.stderr.strip()}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred with '{tool}': {e}")


def _setup_loop_device(img_file):
    """
    Set up a loop device for a disk image.

    :param img_file: Path to the disk image file.
    :return: Loop device name (e.g., /dev/loop0).
    :raises Exception: If loop device setup fails.
    """
    try:
        return run_command(["sudo", "losetup", "--show", "-fP", img_file])
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error setting up loop device: {e.stderr.strip()}")

def _get_partition_info(loop_device):
    """
    Retrieve partition information from a loop device.

    :param loop_device: The loop device (e.g., /dev/loop0).
    :return: List of partitions (e.g., ['/dev/loop0p1', '/dev/loop0p2']).
    """
    try:
        command = ["sudo", "parted", "-s", loop_device, "print"]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        output = result.stdout
        partitions = []
        for line in output.splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():  # Skip empty lines or lines that don't start with a number
                continue
            columns = line.split()
            if len(columns) < 1:
                continue
            partition_number = columns[0]
            partitions.append(f"{loop_device}p{partition_number}")
        click.echo(partitions)
        return partitions
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error retrieving partition info: {e.stderr.strip()}")

def _mount_partition(partition, mount_point):
    """
    Mount a specific partition.

    :param partition: Partition to mount (e.g., /dev/loop0p1).
    :param mount_point: Directory where the partition will be mounted.
    :raises Exception: If mounting fails.
    """
    try:
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        command = ["sudo", "mount", "-o", "ro,noexec", partition, mount_point]
        subprocess.run(command, check=True)
        print(f"Partition {partition} successfully mounted at {mount_point} in read-only mode.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error mounting partition: {e.stderr.strip()}")


def _export_ewf_to_raw(input_files, output_file_name):
    """
        Convert an EWF (E01) disk image series to a raw image using ewfexport.

        :param input_files: List of paths to the input EWF disk image files.
        :param output_file: Path to save the output raw disk image.
        :raises Exception: If the conversion fails.
        """
    try:
        output_dir = os.path.dirname(output_file_name)  # Extract the directory part of the path
        if output_dir:  # Check if there's a directory part in the path
            os.makedirs(output_dir, exist_ok=True)

        # Construct the ewfexport command
        command = ["ewfexport", "-t", output_file_name, "-f", "raw", "-u"] + input_files
        subprocess.run(command, check=True)
        print(f"EWF disk image {', '.join(input_files)} successfully converted to raw disk image {output_file_name}")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error running ewfexport: {e.stderr.strip()}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")