import sys
import os
import stat
import pwd
import grp
from utils.helper import check_path_type, resolve_path, run_command, parse_size_from_string, parse_size_to_string
import click
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from geopy.geocoders import Nominatim

@click.group()
def module():
    """
    Metadata analysis module.
    """
    pass


@module.command()
@click.argument("file_path", type=click.Path())
@click.option("--save-as", type=click.Choice(["json", "xml", "txt"], case_sensitive=False),help="Save metadata as JSON, XML,TXT file.")
@click.option("--save-to", type=click.Path(), help="Path to save metadata to. Users home dir is default")
@click.pass_context
def get_all_metadata(ctx, file_path, save_as: str, save_to: str):
    """
    Get all metadata from file. Does not resolve recursive metadata.

    FILE_PATH is the path to the file to extract metadata from.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        if save_to:
            save_to = resolve_path(ctx.obj['workdir'], save_to)
            check_path_type(ctx.obj['workdir'], save_to, has_to_be_file=False)
    except Exception as e:
        click.echo(e)
        sys.exit()

    # Get basic metadata
    try:
        metadata_raw = run_command(["exiftool", "-j", file_path])
        metadata = json.loads(metadata_raw)[0]
    except Exception as e:
        click.echo(f"Error retrieving metadata: {e}")
        sys.exit()

    # Print metadata to console if no save options are provided
    if not save_as and not save_to:
        click.echo(json.dumps(metadata, indent=4))
        return

    # Ensure save_as is provided if save_to is specified
    if save_to and not save_as:
        click.echo("Invalid arguments. Option --save-as is missing")
        sys.exit()

    # Resolve save_to or default to the
    save_to_dir = save_to or os.path.expanduser("~")
    metadata_filename = _generate_metadata_filename(file_path, "metadata_all")

    # Construct the full save path
    save_path = os.path.join(save_to_dir, f"{metadata_filename}.{save_as.lower()}")

    match save_as.lower():
        case "json":
            _save_metadata_as_json(metadata, save_path)
        case "xml":
            _save_metadata_as_xml(metadata, save_path)
        case "txt":
            _save_metadata_as_txt(metadata, save_path)

@module.command()
@click.argument("file_path", type=click.Path())
@click.option("--save-as", type=click.Choice(["json", "xml", "txt"], case_sensitive=False),help="Save metadata as JSON, XML,TXT file.")
@click.option("--save-to", type=click.Path(), help="Path to save metadata to. Users home dir is default")
@click.option("-l", "--location", is_flag=True, default=False, help="Include estemated location")
@click.pass_context
def get_gps_metadata(ctx, file_path, save_as: str, save_to: str, location: bool):
    """
        Get GPS metadata from the file.

        FILE_PATH is the path to the file to extract metadata from.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        if save_to:
            save_to = resolve_path(ctx.obj['workdir'], save_to)
            check_path_type(ctx.obj['workdir'], save_to, has_to_be_file=False)
    except Exception as e:
        click.echo(e)
        sys.exit()

    # get gps metadata
    try:
        metadata = _get_raw_gps_metadata(file_path)
    except Exception as e:
        click.echo(f"Error retrieving metadata: {e}")
        sys.exit()

        # Add estimated location if the --location flag is used
    if location and "GPSLatitude" in metadata and "GPSLongitude" in metadata:
        try:
            location_info = _estimate_gps_location(metadata)
            metadata["EstimatedLocation"] = location_info.address if location_info else "Unknown location"
        except Exception as e:
            click.echo(f"Error estimating location: {e}")
            metadata["EstimatedLocation"] = "Error in location estimation"

        # Print metadata to console if no save options are provided
    if not save_as and not save_to:
        click.echo(json.dumps(metadata, indent=4))
        return

    # Ensure save_as is provided if save_to is specified
    if save_to and not save_as:
        click.echo("Invalid arguments. Option --save-as is missing")
        sys.exit()

    # Resolve save_to or default to the
    save_to_dir = save_to or os.path.expanduser("~")
    metadata_filename = _generate_metadata_filename(file_path, "metadata_gps")

    # Construct the full save path
    save_path = os.path.join(save_to_dir, f"{metadata_filename}.{save_as.lower()}")

    match save_as.lower():
        case "json":
            _save_metadata_as_json(metadata, save_path)
        case "xml":
            _save_metadata_as_xml(metadata, save_path)
        case "txt":
            _save_metadata_as_txt(metadata, save_path)

@module.command()
@click.argument("dir_path", type=click.Path())
@click.option("--depth", type=click.INT, default=0, help="Depth of recursive search.")
@click.pass_context
def find_files_with_gps(ctx, dir_path, depth):
    """
        Check for GPS metadata in all files within a directory.
        PATH is the directory to search.
    """
    try:
        check_path_type(ctx.obj['workdir'], dir_path, has_to_be_file=False)
        dir_path = resolve_path(ctx.obj['workdir'], dir_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    click.echo(f"Searching for GPS metadata in: {dir_path}")
    files_with_gps = _list_files_with_gps_metadata(dir_path, depth)

    if files_with_gps:
        click.echo(f"Files with GPS metadata ({len(files_with_gps)} found):")
        for file in files_with_gps:
            click.echo(f"- {file}")
    else:
        click.echo("No files with GPS metadata found.")

@module.command()
@click.argument("dir_path", type=click.Path())
@click.option("--less-than", type=click.STRING, help="Find files smaller than this size (e.g., '515 kB').")
@click.option("--more-than", type=click.STRING, help="Find files larger than this size (e.g., '1 GB').")
@click.option("--between", type=(click.STRING, click.STRING), help="Find files with sizes between these values (e.g., '64 MB', '256 MB').")
@click.option("--depth", type=click.INT, default=1, help="Depth of recursive search.")
@click.option("-t", "--type", type=click.Choice(["f","d"], case_sensitive=False), required=True, help="Type of search. File or directory")
@click.pass_context
def find_files_by_size(ctx, dir_path, less_than, more_than, between, depth, type):
    """
        Get list of files or directories based on size.

        DIR_PATH is the path to the directory to search in.
        """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], dir_path, has_to_be_file=False)
        dir_path = resolve_path(ctx.obj['workdir'], dir_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        # Parse size strings into bytes
        less_than = parse_size_from_string(less_than) if less_than else None
        more_than = parse_size_from_string(more_than) if more_than else None
        between = (parse_size_from_string(between[0]), parse_size_from_string(between[1])) if between else None

        if less_than:
            results = _get_size_filtered_results(dir_path, "-", less_than, depth, type)
        elif more_than:
            results = _get_size_filtered_results(dir_path, "+", more_than, depth, type)
        elif between:
            min_size, max_size = between
            if min_size > max_size:
                raise Exception("Invalid input: Minimum size is greater than maximum size.")

            results = _get_size_filtered_results(dir_path, "+", min_size, depth, type)
            results = [
                result for result in results if int(run_command(["stat", "-c", "%s", result[0]])) <= max_size
            ]
        else:
            click.echo("Error: Please provide one of --less-than, --more-than, or --between.")
            return

        # Display results with sizes
        if results:
            click.echo(f"Found {len(results)} matches:")
            for path, size_bytes in results:
                human_readable_size = parse_size_to_string(size_bytes)
                click.echo(f"- {path} ({human_readable_size})")
        else:
            click.echo("No matches found.")
    except Exception as e:
        click.echo(f"Error: {e}")


@module.command()
@click.argument("file_path", type=click.Path())
@click.option("--date-format", type=click.STRING, default="%Y-%m-%d %H:%M:%S", help="Specify the date format. \"Y-%m-%d %H:%M:%S\" is default")
@click.option("--sorted", is_flag=True, help="Sort the output from oldest to newest.")
@click.pass_context
def extract_file_dates(ctx, file_path, date_format, sorted):
    """
        Extract all available dates from a file using exiftool.

        FILE_PATH is the path to the file to process.
        """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        dates = _get_dates_from_file(file_path, date_format, sorted)

        if dates:
            for key, date in dates:
                click.echo(f"{key}: {date}")
        else:
            click.echo("No date metadata found in the file.")
    except Exception as e:
        click.echo(f"Error: {e}")


@module.command()
@click.argument("dir_path", type=click.Path())
@click.option("--date-type", type=click.STRING, default="FileModifyDate", help="Type of metadata date to filter by (default: FileModifyDate).")
@click.option("--older-than", type=click.DateTime(formats=["%Y-%m-%d"]), help="Find files older than this date (YYYY-MM-DD).")
@click.option("--newer-than", type=click.DateTime(formats=["%Y-%m-%d"]), help="Find files newer than this date (YYYY-MM-DD).")
@click.option("--between", type=(click.DateTime(formats=["%Y-%m-%d"]), click.DateTime(formats=["%Y-%m-%d"])), help="Find files between these dates (YYYY-MM-DD).")
@click.option("--file-type", type=click.STRING, help="Filter by file type based on file mime type.")
@click.option("--depth", type=click.INT, default=0, help="Depth of recursive search (default: 0).")
@click.pass_context
def find_files_by_date(ctx, dir_path, date_type, older_than, newer_than, between, file_type, depth):
    """
        Find files in a directory based on metadata date, and file type.

        DIR_PATH is the path to the directory to search in.
    """

    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], dir_path, has_to_be_file=False)
        dir_path = resolve_path(ctx.obj['workdir'], dir_path)

    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        click.echo(dir_path)
        matching_files = _find_files_by_date(dir_path, date_type, older_than, newer_than, between, file_type, depth)
        if matching_files:
            click.echo(f"Found {len(matching_files)} matching files:")
            for file in matching_files:
                click.echo(f"- {file}")
        else:
            click.echo("No matching files found.")
    except Exception as e:
        click.echo(f"Error: {e}")

@module.command()
@click.argument("dir_path", type=click.Path())
@click.option("--mime-type", type=str, help="Filter files by MIME type (e.g., 'image/jpeg').")
@click.option("--extension", type=str, help="Filter files by extension (e.g., 'jpg', 'png').")
@click.option("--depth", type=int, default=0, help="Depth of recursive search (default: 0).")
@click.pass_context
def find_files_by_type(ctx, dir_path, mime_type, extension, depth):
    """
    Find files in a directory based on MIME type or file extension.

    DIR_PATH is the path to the directory to search in.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], dir_path, has_to_be_file=False)
        dir_path = resolve_path(ctx.obj['workdir'], dir_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        matching_files = _find_files_by_type(dir_path, mime_type, extension, depth)

        if matching_files:
            click.echo(f"Found {len(matching_files)} matching files:")
            for file in matching_files:
                click.echo(f"- {file}")
        else:
            click.echo("No matching files found.")
    except Exception as e:
        click.echo(f"Error: {e}")

@module.command()
@click.argument("file_path", type=click.Path())
@click.pass_context
def get_file_mime_type(ctx, file_path):
    """
       Get mime type of the file.

       FILE_PATH is the path to the file.
       """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)

        return _get_file_mime_type(file_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

@module.command()
@click.argument("file_path", type=click.Path())
@click.option("--human", is_flag=True, default=False, help="Display permissions in detailed human-readable format.")
@click.option("--owner", is_flag=True, default=False, help="Display the file owner's name.")
@click.option("--group", is_flag=True, default=False, help="Display the group that has access to the file.")
@click.option("--number", is_flag=True, default=False, help="Display permissions in numeric format.")
@click.pass_context
def get_file_permissions(ctx, file_path, human, owner, group, number):
    """
    Get the permissions, owner, and group of a file.

    FILE_PATH is the path to the file.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        file_info = _get_file_info(file_path, human=human, include_owner=owner, include_group=group, include_number=number)

        click.echo(f"File: {file_path}")

        if human:
            click.echo("Permissions:")
            for category, perms in file_info["permissions"].items():
                click.echo(f"  {category.capitalize()}:")
                for perm, has_perm in perms.items():
                    status = "Yes" if has_perm else "No"
                    click.echo(f"    {perm.capitalize()}: {status}")
        else:
            click.echo(f"Permissions: {file_info['permissions']}")

        if number:
            click.echo(f"Numeric Permissions: {file_info['number']}")

        if owner:
            click.echo(f"Owner: {file_info['owner']}")

        if group:
            click.echo(f"Group: {file_info['group']}")
    except Exception as e:
        click.echo(f"Error: {e}")

@module.command()
@click.argument("dir_path", type=click.Path())
@click.option("--owner", type=str, help="Owner permissions (numeric or symbolic, e.g., 'rw-' or '7').")
@click.option("--group", type=str, help="Group permissions (numeric or symbolic, e.g., 'r--' or '5').")
@click.option("--other", type=str, help="Other permissions (numeric or symbolic, e.g., 'rwx' or '7').")
@click.option("--all", type=str, help="All permissions (e.g., '755').")
@click.option("--depth", type=int, default=0, help="Depth of recursive search (default: 0).")
@click.option("--include-owner", type=str, help="Search for files owned by this user.")
@click.option("--include-special", is_flag=True, default=False, help="Include special bits (SUID, SGID, Sticky Bit).")
@click.pass_context
def find_files_by_permissions(ctx,dir_path, owner, group, other, all, depth, include_owner, include_special):
    """
    Search for files in a directory with specific permissions.

    DIR_PATH is the path to the directory to search.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    try:
        # Parse `--all` or individual permissions
        owner_perm = group_perm = other_perm = None
        if all:
            owner_perm, group_perm, other_perm = _parse_all_permissions(all)
        else:
            owner_perm = _parse_permission_string(owner, include_special=include_special) if owner else None
            group_perm = _parse_permission_string(group, include_special=include_special) if group else None
            other_perm = _parse_permission_string(other, include_special=include_special) if other else None

        # Search for matching files
        matching_files = _search_files_by_permissions(
            dir_path, owner_perm, group_perm, other_perm, include_owner, depth, include_special
        )

        # Display results
        if matching_files:
            click.echo(f"Found {len(matching_files)} matching files:")
            for file in matching_files:
                click.echo(f"- {file}")
        else:
            click.echo("No matching files found.")
    except Exception as e:
        click.echo(f"Error: {e}")
#-------------help functions-------------
def _save_metadata_as_json(metadata, save_path):
    """
    Save metadata to a JSON file.
    """
    try:
        with open(save_path, "w") as f:
            json.dump(metadata, f, indent=4)
        click.echo(f"Metadata saved as JSON to: {save_path}")
    except Exception as e:
        click.echo(f"Error saving metadata: {e}")

def _save_metadata_as_xml(metadata, save_path):
    """
    Save metadata to an XML file.
    """
    try:
        root = ET.Element("metadata")
        for key, value in metadata.items():
            child = ET.SubElement(root, key)
            child.text = str(value)
        tree = ET.ElementTree(root)
        tree.write(save_path)
        click.echo(f"Metadata saved as XML to: {save_path}")
    except Exception as e:
        click.echo(f"Error saving metadata: {e}")

def _save_metadata_as_txt(metadata, save_path):
    """
    Save metadata to a TXT file.
    """
    try:
        with open(save_path, "w") as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        click.echo(f"Metadata saved as TXT to: {save_path}")
    except Exception as e:
        click.echo(f"Error saving metadata: {e}")

def _generate_metadata_filename(file_path, metadata_type):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    # Get the current date in YYYYMMDD format
    current_date = datetime.now().strftime("%Y%m%d%H%M%S")
    # Combine components
    return f"{base_name}-{metadata_type}-{current_date}"

def _estimate_gps_location(gps_object):
    latitude = gps_object["GPSLatitude"]
    longitude = gps_object["GPSLongitude"]
    latitudeReF = gps_object["GPSLatitudeRef"]
    longitudeRef = gps_object["GPSLongitudeRef"]

    latidute = latitude if latitudeReF == "North" else latitude*(-1)
    longitude = longitude if longitudeRef == "East" else longitude*(-1)

    geolocator = Nominatim(user_agent="gps_metadata_tool")
    location_info = geolocator.reverse((latitude, longitude), language="en")

    return location_info

def _get_raw_gps_metadata(file_path):
    metadata_raw = run_command(["exiftool", "-gps:all", "-j", "-c", "%.3f", file_path])
    metadata = json.loads(metadata_raw)[0]

    # Check if GPS metadata exists
    if "GPSVersionID" not in metadata and "GPSLatitude" not in metadata:
        raise Exception("No GPS metadata found")
    return metadata

def _list_files_with_gps_metadata(directory, depth):
    """
    List all files with GPS metadata in a directory up to a given depth.
    :param directory: Path to the directory.
    :param depth: Depth of recursive search. If None, search is unlimited.
    :return: List of file paths with GPS metadata.
    """
    files_with_gps = []

    for root, dirs, files in os.walk(directory):
        # Limit recursion depth if depth is specified
        if depth is not None:
            current_depth = root[len(directory):].count(os.sep)
            if current_depth >= depth:
                dirs[:] = []  # Do not recurse further

        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Attempt to retrieve GPS metadata
                _get_raw_gps_metadata(file_path)
                files_with_gps.append(file_path)  # If no exception, add file to the list
            except Exception:
                # Skip files without GPS metadata or on error
                pass

    return files_with_gps


def _get_size_filtered_results(directory, size_option, size_value, depth, type):
    """
    Use `find` for files or `du` for directories based on size and include sizes in output.
    :param directory: Directory to search in.
    :param size_option: '+' for greater than, '-' for less than.
    :param size_value: Size in bytes.
    :param depth: Maximum depth of recursive search.
    :param type: Search type ('f' for files, 'd' for directories).
    :return: List of tuples (path, size) of matching files or directories.
    """
    results = []

    if type == "f":
        # Use `find` for files
        command = ["find", directory, "-maxdepth", str(depth), "-type", "f", "-size", f"{size_option}{size_value}c"]
        files = run_command(command).splitlines()

        for file_path in files:
            try:
                # Get file size in bytes
                size_bytes = int(run_command(["stat", "-c", "%s", file_path]))
                results.append((file_path, size_bytes))
            except Exception as e:
                click.echo(f"Warning: Could not process file {file_path}: {e}")

    elif type == "d":
        # Use `find` to list directories, then filter by size using `du`
        command = ["find", directory, "-maxdepth", str(depth), "-type", "d"]
        dirs = run_command(command).splitlines()

        for dir_path in dirs:
            try:
                # Get size of directory in bytes using `du`
                du_output = run_command(["du", "-sb", dir_path])
                dir_size = int(du_output.split()[0])  # First column is the size in bytes

                # Check size condition
                if size_option == "+" and dir_size > size_value:
                    results.append((dir_path, dir_size))
                elif size_option == "-" and dir_size < size_value:
                    results.append((dir_path, dir_size))
            except Exception as e:
                click.echo(f"Warning: Could not process directory {dir_path}: {e}")

    return results

def _get_dates_from_file(file_path, date_format, sorted_output):
    """
    Extract all time-related metadata from a file using exiftool.
    :param file_path: Path to the file.
    :param date_format: Optional format for the date output (e.g., '%Y-%m-%d').
    :param dates_only: If True, include only fields with 'date' in their name.
    :param sorted_output: If True, sort the output from oldest to newest.
    :return: List of tuples (key, value).
    """
    try:
        # Run exiftool to get all time-related metadata
        metadata_raw = run_command(["exiftool", "-j", "-time:all", "-dateFormat", "%Y:%m:%d %H:%M:%S", file_path])
        metadata = json.loads(metadata_raw)[0]  # Exiftool outputs a JSON array

        # Filter out GPSTimeStamp and GPSDateStamp
        filtered_metadata = {key: value for key, value in metadata.items() if
                             key not in {"GPSTimeStamp", "GPSDateStamp"}}

        times = []
        for key, raw_time in filtered_metadata.items():
            try:
                from datetime import datetime

                # Parse the raw time using the default ExifTool format
                parsed_time = datetime.strptime(raw_time, "%Y:%m:%d %H:%M:%S")

                # Format the time if a custom date format is provided
                formatted_time = parsed_time.strftime(date_format) if date_format else raw_time

                times.append((key, formatted_time, parsed_time))
            except Exception:
                # Fallback for non-time-related fields
                times.append((key, raw_time, None))

        # Sort results if --sorted is enabled
        if sorted_output:
            times = sorted(
                times,
                key=lambda x: x[2] if x[2] else datetime.max  # Use parsed_time or a max date as fallback
            )

        # Return the final result without parsed_time for cleaner output
        return [(key, value) for key, value, _ in times]

    except Exception as e:
        raise Exception(f"Error processing metadata: {e}")

def _get_file_mime_type(file_path):
    """
    Determine the file type based on its signature using the 'file' command.
    :param file_path: Path to the file.
    :return: Detected file type as a string.
    """
    try:
        result = run_command(["file", "--mime-type", "-b", file_path])
        return result.strip()
    except Exception as e:
        raise Exception(f"Error determining file signature for {file_path}: {e}")


def _find_files_by_date(dir_path, date_type, older_than, newer_than, between, file_type, depth):
    """
    Find files based on date metadata, author, and file type.
    :param dir_path: Directory to search in.
    :param date_type: Metadata date type to filter by.
    :param older_than: Find files older than this date.
    :param newer_than: Find files newer than this date.
    :param between: Find files within this date range.
    :param file_type: Filter by file type signature.
    :param depth: Maximum depth for directory traversal.
    :return: List of matching files.
    """
    matching_files = []
    for root, dirs, files in os.walk(dir_path):
        # Apply depth filter
        current_depth = root[len(dir_path):].count(os.sep)
        if depth == 0 and current_depth > 0:
            # Prevent traversal if depth is 0 (only current directory)
            del dirs[:]
            continue
        if depth is not None and current_depth >= depth:
            # Prevent os.walk from traversing deeper
            del dirs[:]

        for file in files:
            file_path = os.path.join(root, file)

            try:
                # Get file metadata
                metadata_raw = run_command(["exiftool", "-j","-dateFormat", "%Y:%m:%d %H:%M:%S",file_path])
                metadata = json.loads(metadata_raw)[0]

                # Skip files without the specified date type
                if date_type not in metadata:
                    continue

                # Parse the date
                file_date = datetime.strptime(metadata[date_type], "%Y:%m:%d %H:%M:%S")

                # Apply date filters
                if older_than and file_date >= older_than:
                    continue
                if newer_than and file_date <= newer_than:
                    continue
                if between and not (between[0] <= file_date <= between[1]):
                    continue

                # Check file type if specified
                if file_type:
                    detected_type = _get_file_mime_type(file_path)
                    if file_type.lower() not in detected_type.lower():
                        continue

                # File matches all criteria
                matching_files.append(file_path)

            except Exception as e:
                click.echo(f"Warning: Skipping file {file_path}: {e}")

    return matching_files

def _find_files_by_type(dir_path, mime_type, extension, depth):
    """
    Find files based on MIME type or file extension.
    :param dir_path: Directory path to search in.
    :param mime_type: Filter files by MIME type.
    :param extension: Filter files by file extension.
    :param depth: Maximum depth for directory traversal.
    :return: List of matching files.
    """
    matching_files = []
    for root, dirs, files in os.walk(dir_path):
        # Apply depth filter
        current_depth = root[len(dir_path):].count(os.sep)
        if depth == 0 and current_depth > 0:
            # Prevent traversal if depth is 0 (only current directory)
            del dirs[:]
            continue
        if depth is not None and current_depth >= depth:
            # Prevent os.walk from traversing deeper
            del dirs[:]

        for file in files:
            file_path = os.path.join(root, file)

            try:
                # Check MIME type if specified
                if mime_type:
                    detected_mime = _get_file_mime_type(file_path)
                    if mime_type.lower() not in detected_mime.lower():
                        continue

                # Check file extension if specified
                if extension and not file.lower().endswith(f".{extension.lower()}"):
                    continue

                # Add file to results
                matching_files.append(file_path)

            except Exception as e:
                click.echo(f"Warning: Skipping file {file_path}: {e}")

    return matching_files

def _get_file_info(file_path, human=False, include_owner=False, include_group=False, include_number=False):
    """
    Retrieve file permissions, owner, group, and numeric details.

    :param file_path: Path to the file.
    :param human: Whether to display permissions in detailed human-readable format.
    :param include_owner: Whether to include the file owner's name.
    :param include_group: Whether to include the group name.
    :param include_number: Whether to include numeric permissions.
    :return: A dictionary containing file information.
    """
    try:
        # Get the file's stat information
        file_stat = os.stat(file_path)

        # Permissions
        file_mode = file_stat.st_mode
        if human:
            permissions = _parse_file_permissions(file_mode)
        else:
            permissions = stat.filemode(file_mode)

        # Numeric permissions
        numeric_permissions = oct(file_mode & 0o777) if include_number else None

        # File owner
        owner = pwd.getpwuid(file_stat.st_uid).pw_name if include_owner else None

        # Group
        group = grp.getgrgid(file_stat.st_gid).gr_name if include_group else None

        return {
            "permissions": permissions,
            "owner": owner,
            "group": group,
            "number": numeric_permissions,
        }
    except FileNotFoundError:
        raise Exception(f"File not found: {file_path}")
    except KeyError as e:
        raise Exception(f"Error retrieving owner/group for {file_path}: {e}")
    except Exception as e:
        raise Exception(f"Error retrieving file info for {file_path}: {e}")

def _parse_file_permissions(file_mode):
    """
    Parse file permissions into human-readable categories for owner, group, and other.

    :param file_mode: File mode from `os.stat(file_path).st_mode`.
    :return: Dictionary with parsed permissions.
    """
    # Human-readable permissions
    permissions = {
        "owner": {
            "read": bool(file_mode & stat.S_IRUSR),
            "write": bool(file_mode & stat.S_IWUSR),
            "execute": bool(file_mode & stat.S_IXUSR),
            "suid": bool(file_mode & stat.S_ISUID),
        },
        "group": {
            "read": bool(file_mode & stat.S_IRGRP),
            "write": bool(file_mode & stat.S_IWGRP),
            "execute": bool(file_mode & stat.S_IXGRP),
            "sgid": bool(file_mode & stat.S_ISGID),
        },
        "other": {
            "read": bool(file_mode & stat.S_IROTH),
            "write": bool(file_mode & stat.S_IWOTH),
            "execute": bool(file_mode & stat.S_IXOTH),
            "sticky": bool(file_mode & stat.S_ISVTX),
        },
    }
    return permissions

def _search_files_by_permissions(dir_path, owner_perm, group_perm, other_perm, owner_name, depth, include_special):
    """
    Search for files with specific permissions in a directory, including non-standard bits.
    :param dir_path: Directory path to search.
    :param owner_perm: Owner permission.
    :param group_perm: Group permission.
    :param other_perm: Other permission.
    :param owner_name: Specific owner name to match.
    :param depth: Depth of search (0 for current directory only).
    :param include_special: Whether to include SUID, SGID, and Sticky Bit checks.
    :return: List of matching files.
    """
    matching_files = []
    for root, dirs, files in os.walk(dir_path):
        # Apply depth limit
        current_depth = root[len(dir_path):].count(os.sep)
        if depth == 0 and current_depth > 0:
            del dirs[:]
            continue
        if depth is not None and current_depth >= depth:
            del dirs[:]

        for file in files:
            file_path = os.path.join(root, file)
            try:
                file_stat = os.stat(file_path)

                # Match permissions, including special bits
                if not _match_permissions_with_special(file_stat.st_mode, owner_perm, group_perm, other_perm, include_special):
                    continue

                # Match owner if specified
                if owner_name:
                    file_owner = pwd.getpwuid(file_stat.st_uid).pw_name
                    if file_owner != owner_name:
                        continue

                # File matches criteria
                matching_files.append(file_path)
            except Exception as e:
                click.echo(f"Warning: Could not process file {file_path}: {e}")
    return matching_files

def _match_permissions_with_special(file_mode, owner_perm, group_perm, other_perm, include_special=False):
    """
    Check if a file's mode matches the given permissions, including special bits.
    :param file_mode: File mode from os.stat.
    :param owner_perm: Integer owner permission.
    :param group_perm: Integer group permission.
    :param other_perm: Integer other permission.
    :param include_special: Whether to include SUID, SGID, and Sticky Bit checks.
    :return: True if permissions match, otherwise False.
    """
    # Extract permissions for owner, group, and other
    owner = (file_mode & 0o700) >> 6
    group = (file_mode & 0o070) >> 3
    other = file_mode & 0o007

    # Check non-standard bits
    suid = bool(file_mode & stat.S_ISUID) if include_special else None
    sgid = bool(file_mode & stat.S_ISGID) if include_special else None
    sticky = bool(file_mode & stat.S_ISVTX) if include_special else None

    return (
        (owner_perm is None or owner == owner_perm) and
        (group_perm is None or group == group_perm) and
        (other_perm is None or other == other_perm) and
        (not include_special or suid is not None or sgid is not None or sticky is not None)
    )

def _parse_permission_string(permission_str, include_special=False):
    """
    Convert a permission string (e.g., 'r--', 'rw-', '7', 's', 't') to an integer value.
    :param permission_str: Permission string (e.g., 'r--', 'rw-', '7', 's').
    :param include_special: Whether to handle SUID, SGID, and Sticky Bit (symbolic: 's', 't').
    :return: Integer representation of permissions.
    """
    if permission_str.isdigit():
        # Convert numeric permission
        return int(permission_str)

    # Symbolic permission (e.g., 'rw-s')
    permission_map = {"r": 4, "w": 2, "x": 1, "-": 0}
    special_map = {"s": 4, "t": 1}

    total = sum(permission_map[char] for char in permission_str if char in permission_map)
    if include_special:
        for char in permission_str:
            if char in special_map:
                total += special_map[char]

    return total

def _parse_all_permissions(permission_str):
    """
    Parse the `--all` option to split permissions for owner, group, and other.
    :param permission_str: A numeric string (e.g., '755') or symbolic string (e.g., 'rwxr-xr-x').
    :return: A tuple (owner_perm, group_perm, other_perm).
    """
    if permission_str.isdigit() and len(permission_str) == 3:
        # Numeric permissions (e.g., '755')
        owner_perm = int(permission_str[0])
        group_perm = int(permission_str[1])
        other_perm = int(permission_str[2])
        return owner_perm, group_perm, other_perm
    elif len(permission_str) == 9:
        # Symbolic permissions (e.g., 'rwxr-xr-x')
        owner_perm = _parse_permission_string(permission_str[:3])  # First 3 characters
        group_perm = _parse_permission_string(permission_str[3:6])  # Middle 3 characters
        other_perm = _parse_permission_string(permission_str[6:])  # Last 3 characters
        return owner_perm, group_perm, other_perm
    else:
        raise ValueError("--all must be a 3-digit numeric string (e.g., '755') or a 9-character symbolic string (e.g., 'rwxr-xr-x').")