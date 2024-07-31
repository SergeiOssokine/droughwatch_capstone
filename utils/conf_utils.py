import logging
from typing import Dict, List, Union

from omegaconf import DictConfig, OmegaConf
from rich.logging import RichHandler
from rich.traceback import install

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


def dict_generator(adict: Union[Dict, List, str, float], pre: List = None):
    """Recursively traverse a nested dict and return a list with a
    path to each value. See  here:
    https://stackoverflow.com/a/73430155/22288495

    Args:
        adict (Union[Dict,List,str,float]): The current item being traversed
        pre (List, optional): Current path. Defaults to None.

    Yields:
        List: The full path to every item
    """
    pre = pre[:] if pre else []
    if isinstance(adict, dict):
        for key, value in adict.items():
            if isinstance(value, dict):
                yield from dict_generator(value, pre + [key])
            elif isinstance(value, (list, tuple)):
                for v in value:
                    yield from dict_generator(v, pre + [key])
            else:
                yield pre + [key, value]
    else:
        yield pre + [adict]


def validate_dict(cfg: DictConfig) -> None:
    """Iterate over the configuration and check for unset (None)
    values, then hilight those if found and exit

    Args:
        cfg (DictConfig): Top-level config for the project
    """
    fail = False
    conf = OmegaConf.to_container(cfg, resolve=True, throw_on_missing=True)

    gen = dict_generator(conf)
    for item in gen:
        param = ".".join(item[:-1])
        val = item[-1]
        if val is None:
            logger.error(f"{param} is unset. Please examine the top-level config file")
            fail = True
    if fail:
        logger.critical("Validation failed! Exiting")
        exit(1)
