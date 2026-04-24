set unstable

set windows-shell := ["pwsh", "-NoLogo", "-NoProfileLoadTime", "-Command"]
set script-interpreter := ["uv", "run", "python"]


default:
    @just --list --unsorted

[doc("Compile Python code to bytecode")]
compile:
    uv run --compile-bytecode python -c ""

[doc("Run tests with pytest")]
test:
    uv run --dev pytest

[doc("Run ruff for formatting")]
format:
    - uvx ruff format
    uvx ruff check --select I --fix

[doc("Run linting with ruff")]
check:
    uvx ruff check --exclude src/libs

[doc("Run ty type checking")]
ty:
    uvx ty check --exclude src/libs

[doc("Display README.md in terminal")]
[script]
help:
    from rich.console import Console
    from rich.markdown import Markdown

    console = Console()
    with open("README.md", "r", encoding="utf-8") as readme:
        markdown = Markdown(readme.read())
    console.print(markdown)
