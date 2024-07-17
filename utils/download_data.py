import logging
import os
import zipfile

import requests
import typer
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.traceback import install
from typing_extensions import Annotated

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("CRITICAL")
# Setup rich to get nice tracebacks
install()

data_url = "https://storage.googleapis.com/wandb_datasets/dw_train_86K_val_10K.zip"
data_url = "https://download.brainvoyager.com/bv/data/BrainTutorData.zip"
filepath = "./training/data/data.zip"


def main(
    extract: Annotated[
        bool, typer.Option(help="Extract the data from the archive")
    ] = True,
    verbose: Annotated[bool, typer.Option(help="Provide verbose progress")] = True,
):
    if verbose:
        logger.setLevel("INFO")
    response = requests.get(data_url, stream=True)
    if not response.ok:
        logger.critical(f"Got response code {response.status_code} from {data_url}")
        raise ValueError
    logger.info("Downloading the training and validation data")
    logger.info(f"URL: {data_url}")
    # Sizes in bytes.
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024
    progress = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
    )
    filename = os.path.basename(data_url)
    task_id = progress.add_task(
        "download", filename=filename, start=False, total=total_size
    )
    with progress:
        with open(filepath, "wb") as dest_file:
            progress.start_task(task_id)
            for data in response.iter_content(block_size):
                size = dest_file.write(data)
                progress.update(task_id, advance=size)

    logger.info(f"Downloaded {filename}")
    if extract:
        dest = "./training/data"
        logger.info(f"Extracting archive to {dest}")
        with zipfile.ZipFile(filepath, "r") as zip_ref:
            zip_ref.extractall(dest)
        logger.info("Done")


if __name__ == "__main__":
    typer.run(main)
