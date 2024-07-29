from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty


def print_difference(expected, received):
    panel1 = Panel(Pretty(expected), title="Expected", expand=False)
    panel2 = Panel(Pretty(received), title="Received", expand=False)

    # Create a Columns object with the two panels
    columns = Columns([panel1, panel2])

    # Create a Console object and print the columns
    console = Console()
    console.print(columns)
