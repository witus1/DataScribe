import sys
import os
from utils.helper import check_path_type, resolve_path, run_command
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
@click.option("--date-less-than", type=click.DateTime(), help="Find files with dates earlier than this.")
@click.option("--date-greater-than", type=click.DateTime(), help="Find files with dates later than this.")
@click.pass_context
def search_by_date(ctx:click.Context, date_less_than, date_greater_than, path):
    """
    Search files by metadata dates.
    """
    pass

@module.command()
@click.argument("file_path", type=click.Path())
@click.option("--save-as", type=click.Choice(["json", "xml", "txt"], case_sensitive=False),help="Save metadata as JSON, XML,TXT file.")
@click.option("--save-to", type=click.STRING, help="Path to save metadata to. Users home dir is default")
@click.pass_context
def get_metadata_all(ctx, file_path, save_as: str, save_to: str):
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
        metadata_raw = run_command(["exiftool", "-j", file_path])  # Use -j for JSON-like output
        metadata = json.loads(metadata_raw)[0]  # Exiftool outputs JSON array
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
    metadata_filename = generate_metadata_filename(file_path, "metadata_all")

    # Construct the full save path
    save_path = os.path.join(save_to_dir, f"{metadata_filename}.{save_as.lower()}")

    match save_as.lower():
        case "json":
            save_metadata_as_json(metadata, save_path)
        case "xml":
            save_metadata_as_xml(metadata, save_path)
        case "txt":
            save_metadata_as_txt(metadata, save_path)

@module.command()
@click.argument("file_path", type=click.Path())
@click.option("--save-as", type=click.Choice(["json", "xml", "txt"], case_sensitive=False),help="Save metadata as JSON, XML,TXT file.")
@click.option("--save-to", type=click.Path(), help="Path to save metadata to. Users home dir is default")
@click.option("-l", "--location", is_flag=True, default=False, help="Include estemated location")
@click.pass_context
def get_metadata_gps(ctx, file_path, save_as: str, save_to: str, location: bool):
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
        metadata = get_raw_gps_metadata(file_path)
    except Exception as e:
        click.echo(f"Error retrieving metadata: {e}")
        sys.exit()

        # Add estimated location if the --location flag is used
    if location and "GPSLatitude" in metadata and "GPSLongitude" in metadata:
        try:
            location_info = estimate_gps_location(metadata)
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
    metadata_filename = generate_metadata_filename(file_path, "metadata_gps")

    # Construct the full save path
    save_path = os.path.join(save_to_dir, f"{metadata_filename}.{save_as.lower()}")

    match save_as.lower():
        case "json":
            save_metadata_as_json(metadata, save_path)
        case "xml":
            save_metadata_as_xml(metadata, save_path)
        case "txt":
            save_metadata_as_txt(metadata, save_path)

@module.command()
@click.argument("dir_path", type=click.Path())
@click.option("--depth", type=click.INT, default=0, help="Depth of recursive search.")
@click.pass_context
def get_files_with_gps(ctx, dir_path, depth):
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
    files_with_gps = list_files_with_gps_metadata(dir_path, depth)

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
def find_size_based(ctx, dir_path, less_than, more_than, between, depth, type):
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
            results = get_size_filtered_results(dir_path, "-", less_than, depth, type)
        elif more_than:
            results = get_size_filtered_results(dir_path, "+", more_than, depth, type)
        elif between:
            min_size, max_size = between
            if min_size > max_size:
                raise Exception("Invalid input: Minimum size is greater than maximum size.")

            results = get_size_filtered_results(dir_path, "+", min_size, depth, type)
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

#-------------help functions-------------
def save_metadata_as_json(metadata, save_path):
    """
    Save metadata to a JSON file.
    """
    try:
        with open(save_path, "w") as f:
            json.dump(metadata, f, indent=4)
        click.echo(f"Metadata saved as JSON to: {save_path}")
    except Exception as e:
        click.echo(f"Error saving metadata: {e}")

def save_metadata_as_xml(metadata, save_path):
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

def save_metadata_as_txt(metadata, save_path):
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

def generate_metadata_filename(file_path, metadata_type):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    # Get the current date in YYYYMMDD format
    current_date = datetime.now().strftime("%Y%m%d%H%M%S")
    # Combine components
    return f"{base_name}-{metadata_type}-{current_date}"

def estimate_gps_location(gps_object):
    latitude = gps_object["GPSLatitude"]
    longitude = gps_object["GPSLongitude"]
    latitudeReF = gps_object["GPSLatitudeRef"]
    longitudeRef = gps_object["GPSLongitudeRef"]

    latidute = latitude if latitudeReF == "North" else latitude*(-1)
    longitude = longitude if longitudeRef == "East" else longitude*(-1)

    geolocator = Nominatim(user_agent="gps_metadata_tool")
    location_info = geolocator.reverse((latitude, longitude), language="en")

    return location_info

def get_raw_gps_metadata(file_path):
    metadata_raw = run_command(["exiftool", "-gps:all", "-j", "-c", "%.3f", file_path])
    metadata = json.loads(metadata_raw)[0]

    # Check if GPS metadata exists
    if "GPSVersionID" not in metadata and "GPSLatitude" not in metadata:
        raise Exception("No GPS metadata found")
    return metadata

def list_files_with_gps_metadata(directory, depth):
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
                get_raw_gps_metadata(file_path)
                files_with_gps.append(file_path)  # If no exception, add file to the list
            except Exception:
                # Skip files without GPS metadata or on error
                pass

    return files_with_gps

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

def get_size_filtered_results(directory, size_option, size_value, depth, type):
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
