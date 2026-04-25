import rich_click as click

from slurm_client.app import SlurmClient
from slurm_client.config import Config


@click.command()
@click.argument("server", type=str)
@click.argument("api-address", type=str)
def main(server: str, api_address: str) -> None:
    config = Config(server=server, address=api_address)

    app = SlurmClient(config)
    app.run()
