import sys
import os
from importlib.metadata import metadata

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

