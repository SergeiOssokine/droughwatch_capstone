from typing import Any, Dict

import docker
from omegaconf import DictConfig, OmegaConf
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty


def launch_lambda_container(name: str, config: DictConfig) -> Any:
    """Launch the lambda container and override the CMD to the
    appropriate name specified by name.

    Args:
        name (str): The name of the CMD override
        config (DictConfig): The configuration dict

    Returns:
        Any: The container
    """
    client = docker.from_env()
    container = client.containers.run(
        config.image,
        command=[f"lambda_function_{name}.lambda_handler"],
        environment=OmegaConf.to_container(config, resolve=True, throw_on_missing=True),
        network_mode="host",
        detach=True,
    )
    return container


def clean_up(container) -> None:
    """Stop and remove the given docker container

    Args:
        container (docker.container): The container to clean up
    """
    container.stop()
    container.remove()


def print_difference(expected: Dict[str, Any], received: Dict[str, Any]) -> None:
    """Pretty print the 2 dictionaries side-by-side so it's easier to see
    any differences

    Args:
        expected (Dict[str,Any]): The expected dict result
        received (Dict[str,Any]): The actual result
    """
    panel1 = Panel(Pretty(expected), title="Expected", expand=False)
    panel2 = Panel(Pretty(received), title="Received", expand=False)

    # Create a Columns object with the two panels
    columns = Columns([panel1, panel2])

    # Create a Console object and print the columns
    console = Console()
    console.print(columns)
