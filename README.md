# Nob.py

> Reasonable defaults for [Click](https://click.palletsprojects.com/en/stable/) CLI applications with rich logging...<br>
> ... and additional goodies.

## Installation

```sh
uv add git+https://github.com/ThomasByr/nob.py --branch main
```

or lock a specific version:

```sh
uv add git+https://github.com/ThomasByr/nob.py --tag v0.1.0
```

## Usage

```py
import logging

from nob import cli


@cli.grp
def main(): ...


@cli.opt("-l", "--log", is_flag=True, help="Prints log messages.")
@cli.cmd(main)
def test(lg: logging.Logger, log: bool = False):

    if log:
        lg.debug("This is a debug message.")
        lg.info("This is an info message.")
        lg.warning("This is a warning message.")
        lg.error("This is an error message.")
        lg.critical("This is a critical message.")


if __name__ == "__main__":
    main()

```

run with:

```sh
uv run <file.py> -v test -l
```

## Contributing

```sh
git clone git@github.com:ThomasByr/nob.py nob
```
