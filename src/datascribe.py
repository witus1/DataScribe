import click

@click.command()
@click.option("--name", help='Name of the user', prompt="Enter your name")
def cli(name):
    click.echo(f"Hello {name}")




if __name__ == "__main__":
    cli()