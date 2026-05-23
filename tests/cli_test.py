import logging

import rich_click as click
from click.testing import CliRunner

from nob import cli
from nob.cli.config import CLIMutex, Config


def test_decorator_order_option_before_cmd():
    runner = CliRunner()

    @cli.opt("--name", required=True)
    @cli.cmd()
    def hello(name):
        print(f"Hello {name}")

    res = runner.invoke(hello, ["--name", "Eric"])
    assert res.exit_code == 0
    assert "Hello Eric" in res.output


def test_decorator_order_cmd_before_option():
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--name", required=True)
    def hello(name):
        print(f"Hello {name}")

    res = runner.invoke(hello, ["--name", "Eric"])
    assert res.exit_code == 0
    assert "Hello Eric" in res.output


def test_cmd_injections():
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--name", required=True)
    def hello(cfg: Config, ctx, lg: logging.Logger, name: str):
        # Will raise AssertionError if injections are wrong
        assert isinstance(cfg, Config)
        assert isinstance(ctx, click.Context)
        assert isinstance(lg, logging.Logger)
        print("INJECTIONS OK")

    res = runner.invoke(hello, ["--name", "Eric"])
    assert res.exit_code == 0
    assert "INJECTIONS OK" in res.output


def test_group_options_log_file_and_verbosity(tmp_path):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--name", required=True)
    def show(cfg: Config, name: str):
        print(f"{cfg.log_level}:{cfg.log_file}:{name}")

    log_path = tmp_path / "log.txt"
    res = runner.invoke(show, ["--verbose", "--log-file", str(log_path), "--name", "Eric"])
    assert res.exit_code == 0
    assert f"{logging.DEBUG}:{str(log_path)}:Eric" in res.output


def test_aliased_group(tmp_path):
    runner = CliRunner()
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text("aliases:\n  h: hello\n")

    @cli.grp()
    def main():
        pass

    @cli.cmd(grp=main)
    @cli.opt("--name", required=True)
    def hello(name: str):
        print(f"Hello {name}")

    res = runner.invoke(main, ["--config", str(cfg_file), "h", "--name", "Eric"])
    assert res.exit_code == 0
    assert "Hello Eric" in res.output


def test_climutex_mutual_exclusion():
    runner = CliRunner()

    @click.option("-a", "--a", is_flag=True, cls=CLIMutex, not_required_if=["b"])
    @click.option("-b", "--b", is_flag=True, cls=CLIMutex, not_required_if=["a"])
    @cli.cmd()
    def main(a: bool, b: bool):
        print(f"{a},{b}")

    res = runner.invoke(main, ["--a", "--b"])
    assert res.exit_code != 0
    assert "mutually exclusive" in res.output.lower()
