from utils.helper import check_path_type, resolve_path
import click

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