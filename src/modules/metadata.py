import sys
import os
from utils.helper import check_path_type, resolve_path, run_command
import click
import json
import xml.etree.ElementTree as ET
from datetime import datetime

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
@click.argument("file_path", type=click.STRING)
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

    # Resolve save_to or default to the user's home directory
    save_to_dir = save_to or os.path.expanduser("~")

    # Generate the metadata filename
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



#help functions
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