import sys
import click
from utils.helper import check_path_type, run_command

from utils.helper import resolve_path


@click.group()
def module():
    """
    Filesystem analysis module.
    """
    pass

#todo has to be finished
@module.command()
@click.option('--path', required=True, type=click.STRING, help='Path where image file is located.')
@click.pass_context
def get_disk_partition_info(ctx:click.Context, path):
    try:
        check_path_type(ctx.obj['workdir'], path, has_to_be_file=True)
    except Exception as e:
        click.echo(e)
        sys.exit()

    dict = get_disk_partition_info_to_dictionary(resolve_path(ctx.obj['workdir'], path))
    click.echo(dict)

#helper functions
#todo has to be finished
def get_disk_partition_info_to_dictionary(path):

    run_command_result = run_command(['fdisk', '-l', path])


    fdisk_info = {"disk": {}, "partitions": []}
    lines = run_command_result.splitlines()

    for line in lines:
        line = line.strip()

        # General Disk Information
        if line.startswith("Disk "):
            # Example: Disk /dev/loop0: 4 GiB, 4294967296 bytes, 8388608 sectors
            parts = line.split(",")
            disk_description = parts[0]
            size_info = parts[1] if len(parts) > 1 else None

            # Parse disk description
            disk_parts = disk_description.split()
            if len(disk_parts) >= 2:
                fdisk_info["disk"]["device"] = disk_parts[1].strip(":")
                fdisk_info["disk"]["size"] = " ".join(disk_parts[2:])

            # Parse size information
            if size_info:
                size_parts = size_info.split()
                if len(size_parts) >= 2:
                    fdisk_info["disk"]["bytes"] = size_parts[0]
                    fdisk_info["disk"]["sectors"] = size_parts[-2]

        # Partition Information
        # if line.startswith("/dev/"):
        #     # Example: /dev/loop0p1       2048    4095    2048  1M  Linux
        #     parts = line.split()
        #     if len(parts) >= 6:
        #         partition_info = {
        #             "device": parts[0],
        #             "start": parts[1],
        #             "end": parts[2],
        #             "sectors": parts[3],
        #             "size": parts[4],
        #             "type": " ".join(parts[5:]),
        #         }
        #         fdisk_info["partitions"].append(partition_info)

    return fdisk_info