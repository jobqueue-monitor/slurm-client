import rich_click as click

from slurm_client.app import SlurmClient
from slurm_client.config import Config


@click.command()
@click.argument("server", type=str)
@click.argument("api-address", type=str)
@click.pass_context
def main(ctx: click.Context, server: str, api_address: str) -> None:
    config = Config(server=server, address=api_address)

    app = SlurmClient(config)
    app.run()

    ctx.exit(app.return_code or 0)
