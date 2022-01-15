"""Command-line interface."""
import click


@click.command()
@click.version_option()
def main() -> None:
    """Afesta Tools."""


if __name__ == "__main__":
    main(prog_name="afesta-tools")  # pragma: no cover
