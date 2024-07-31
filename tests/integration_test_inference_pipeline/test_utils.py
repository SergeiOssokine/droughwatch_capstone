import docker
from omegaconf import DictConfig, OmegaConf
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty


def launch_lambda_container(name: str, config: DictConfig):
    client = docker.from_env()
    container = client.containers.run(
        config.image,
        command=[f"lambda_function_{name}.lambda_handler"],
        environment=OmegaConf.to_container(config, resolve=True, throw_on_missing=True),
        network_mode="host",
        detach=True,
    )
    return container


def clean_up(container):
    container.stop()
    container.remove()


def print_difference(expected, received):
    panel1 = Panel(Pretty(expected), title="Expected", expand=False)
    panel2 = Panel(Pretty(received), title="Received", expand=False)

    # Create a Columns object with the two panels
    columns = Columns([panel1, panel2])

    # Create a Console object and print the columns
    console = Console()
    console.print(columns)
