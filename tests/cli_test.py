import logging

import pytest
import rich_click as click
from click.testing import CliRunner

from nob import cli
from nob.cli.config import CLIMutex, Config


@pytest.mark.parametrize("name", ["Eric", "John Doe", ""])
def test_decorator_order_option_before_cmd(name):
    runner = CliRunner()

    @cli.opt("--name", required=True)
    @cli.cmd()
    def hello(name):
        print(f"Hello {name}")

    res = runner.invoke(hello, ["--name", name])
    assert res.exit_code == 0
    assert f"Hello {name}" in res.output


@pytest.mark.parametrize("name", ["Eric", "John Doe", ""])
def test_decorator_order_cmd_before_option(name):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--name", required=True)
    def hello(name):
        print(f"Hello {name}")

    res = runner.invoke(hello, ["--name", name])
    assert res.exit_code == 0
    assert f"Hello {name}" in res.output


@pytest.mark.parametrize("name", ["Eric", "Alicia"])
def test_cmd_injections(name):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--name", required=True)
    def hello(cfg: Config, ctx, lg: logging.Logger, name: str):
        # Will raise AssertionError if injections are wrong
        assert isinstance(cfg, Config)
        assert isinstance(ctx, click.Context)
        assert isinstance(lg, logging.Logger)
        print("INJECTIONS OK")

    res = runner.invoke(hello, ["--name", name])
    assert res.exit_code == 0
    assert "INJECTIONS OK" in res.output


@pytest.mark.parametrize(
    "logging_flag, log_file_flag, log_level",
    [
        ("--verbose", "--log-file", logging.DEBUG),
        ("-v", "-l", logging.DEBUG),
        ("--quiet", "--log-file", logging.WARNING),
        ("-q", "-l", logging.WARNING),
    ],
)
def test_group_options_log_file_and_verbosity(tmp_path, logging_flag, log_file_flag, log_level):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--name", required=True)
    def show(cfg: Config, name: str):
        print(f"{cfg.log_level}:{cfg.log_file}:{name}")

    log_path = tmp_path / "log.txt"
    res = runner.invoke(show, [logging_flag, log_file_flag, str(log_path), "--name", "Eric"])
    assert res.exit_code == 0
    assert f"{log_level}:{str(log_path)}:Eric" in res.output


@pytest.mark.parametrize(
    "config_flag, alias, expected_name",
    [
        ("--config", "h", "Eric"),
        ("-c", "h", "Alicia"),
    ],
)
def test_aliased_group(tmp_path, config_flag, alias, expected_name):
    runner = CliRunner()
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(f"aliases:\n  {alias}: hello\n")

    @cli.grp()
    def main():
        pass

    @cli.cmd(grp=main)
    @cli.opt("--name", required=True)
    def hello(name: str):
        print(f"Hello {name}")

    res = runner.invoke(main, [config_flag, str(cfg_file), alias, "--name", expected_name])
    assert res.exit_code == 0
    assert f"Hello {expected_name}" in res.output


@pytest.mark.parametrize(
    "args, expected_exit",
    [
        (["--a", "--b"], 2),
        (["-a", "-b"], 2),
        (["--a"], 0),
        (["--b"], 0),
        (["-a"], 0),
        (["-b"], 0),
        ([], 0),
    ],
)
def test_climutex_mutual_exclusion(args, expected_exit):
    runner = CliRunner()

    @click.option("-a", "--a", is_flag=True, cls=CLIMutex, not_required_if=["b"])
    @click.option("-b", "--b", is_flag=True, cls=CLIMutex, not_required_if=["a"])
    @cli.cmd()
    def main(a: bool, b: bool):
        print("SUCCESS")

    res = runner.invoke(main, args)
    assert res.exit_code == expected_exit
    if expected_exit != 0:
        assert "mutually exclusive" in res.output.lower()
    else:
        assert "SUCCESS" in res.output


@pytest.mark.parametrize(
    "args, expected_stdout",
    [
        ([], "DEFAULT EXEC"),
        (["other"], "OTHER EXEC"),
        (["default_cmd"], "DEFAULT EXEC"),
    ],
)
def test_grp_default_command(args, expected_stdout):
    runner = CliRunner()

    @cli.cmd()
    def default_cmd():
        print("DEFAULT EXEC")

    @cli.grp(default=lambda: default_cmd)
    def main():
        pass

    # The default command isn't automatically added to the group in this pattern.
    main.add_command(default_cmd)

    @cli.cmd(grp=main)
    def other():
        print("OTHER EXEC")

    res = runner.invoke(main, args)
    assert res.exit_code == 0
    assert expected_stdout in res.output


@pytest.mark.parametrize(
    "args, expected_exit, expected_output",
    [
        (["u"], 0, "UPDATE"),
        (["update"], 0, "UPDATE"),
        (["inst"], 0, "INSTALL"),
        (["insp"], 0, "INSPECT"),
        (["test"], 0, "TEST"),
        (["t"], 0, "TEST"),
        (["i"], 2, "too many matches: inspect, install"),
        (["in"], 2, "too many matches: inspect, install"),
        (["ins"], 2, "too many matches: inspect, install"),
        (["x"], 2, "no such command"),
    ],
)
def test_aliased_group_prefix_matching(args, expected_exit, expected_output):
    runner = CliRunner()

    @cli.grp()
    def main():
        pass

    @cli.cmd(grp=main)
    def install():
        print("INSTALL")

    @cli.cmd(grp=main)
    def inspect():
        print("INSPECT")

    @cli.cmd(grp=main)
    def update():
        print("UPDATE")

    @cli.cmd(grp=main)
    def test():
        print("TEST")

    res = runner.invoke(main, args)
    assert res.exit_code == expected_exit
    if expected_exit != 0:
        assert expected_output.lower() in res.output.lower()
    else:
        assert expected_output in res.output


@pytest.mark.parametrize(
    "args, expected_level, expects_error",
    [
        ([], logging.INFO, False),
        (["-v"], logging.DEBUG, False),
        (["--verbose"], logging.DEBUG, False),
        (["-q"], logging.WARNING, False),
        (["--quiet"], logging.WARNING, False),
        (["-v", "-q"], None, True),
        (["--verbose", "--quiet"], None, True),
    ],
)
def test_verbosity_and_quiet_config(args, expected_level, expects_error):
    runner = CliRunner()

    @cli.cmd()
    def main(cfg: Config):
        print(f"LEVEL:{cfg.log_level}")

    res = runner.invoke(main, args)
    if expects_error:
        assert res.exit_code != 0
        assert "mutually exclusive" in res.output.lower()
    else:
        assert res.exit_code == 0
        assert f"LEVEL:{expected_level}" in res.output


@pytest.mark.parametrize(
    "cmd_name, expected_output",
    [
        ("no_args", "NO ARGS OK"),
        ("with_kwargs", "HAS CFG:True, HAS CTX:True, HAS LG:True"),
        ("some_args", "SOME ARGS OK"),
    ],
)
def test_smart_injection_constraints(cmd_name, expected_output):
    runner = CliRunner()

    @cli.grp()
    def main():
        pass

    @cli.cmd(grp=main)
    def no_args():
        print("NO ARGS OK")

    @cli.cmd(grp=main)
    def with_kwargs(**kwargs):
        has_cfg = "cfg" in kwargs
        has_ctx = "ctx" in kwargs
        has_lg = "lg" in kwargs
        print(f"HAS CFG:{has_cfg}, HAS CTX:{has_ctx}, HAS LG:{has_lg}")

    @cli.cmd(grp=main)
    def some_args(cfg: Config, name: str = "default"):
        assert isinstance(cfg, Config)
        print("SOME ARGS OK")

    res = runner.invoke(main, [cmd_name])
    assert res.exit_code == 0
    assert expected_output in res.output
