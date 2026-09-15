import logging
from typing import Any

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
    "cmd_log_file, cmd_max_bytes, cmd_backup_count, cli_log_file, cli_max_bytes, cli_backup_count",
    [
        # Nothing specified -> defaults (None, the logging layer applies 10 MB / 5)
        (None, None, None, None, None, None),
        # Only @cli.cmd arguments -> they override the defaults
        ("cmd.log", 111, 1, None, None, None),
        ("cmd.log", None, None, None, None, None),
        (None, 111, None, None, None, None),
        (None, None, 1, None, None, None),
        # Only CLI options -> they override the defaults
        (None, None, None, "cli.log", 222, 2),
        (None, None, None, "cli.log", None, None),
        (None, None, None, None, 222, None),
        (None, None, None, None, None, 2),
        # CLI overrides @cli.cmd on every parameter
        ("cmd.log", 111, 1, "cli.log", 222, 2),
        # CLI wins where given, @cli.cmd fills the gaps
        ("cmd.log", 111, 1, "cli.log", None, None),
        ("cmd.log", 111, 1, None, 222, None),
        ("cmd.log", 111, 1, None, None, 2),
        (None, 111, 1, "cli.log", None, None),
        ("cmd.log", None, 1, None, 222, None),
        ("cmd.log", 111, None, None, None, 2),
    ],
)
def test_log_file_options_precedence(
    tmp_path,
    cmd_log_file,
    cmd_max_bytes,
    cmd_backup_count,
    cli_log_file,
    cli_max_bytes,
    cli_backup_count,
):
    """Precedence of the log file options: CLI > @cli.cmd arguments > defaults."""
    runner = CliRunner()

    cmd_kwargs: dict[str, Any] = {}
    if cmd_log_file is not None:
        cmd_kwargs["log_file"] = str(tmp_path / cmd_log_file)
    if cmd_max_bytes is not None:
        cmd_kwargs["log_file_max_bytes"] = cmd_max_bytes
    if cmd_backup_count is not None:
        cmd_kwargs["log_file_backup_count"] = cmd_backup_count

    args = []
    if cli_log_file is not None:
        args += ["--log-file", str(tmp_path / cli_log_file)]
    if cli_max_bytes is not None:
        args += ["--log-file-max-bytes", str(cli_max_bytes)]
    if cli_backup_count is not None:
        args += ["--log-file-backup-count", str(cli_backup_count)]

    @cli.cmd(**cmd_kwargs)
    def main(cfg: Config):
        print(f"FILE:{cfg.log_file}|MAX:{cfg.log_file_max_bytes}|BACKUP:{cfg.log_file_backup_count}")

    res = runner.invoke(main, args)
    assert res.exit_code == 0

    expected_log_file = (
        str(tmp_path / (cli_log_file or cmd_log_file)) if (cli_log_file or cmd_log_file) else None
    )
    expected_max_bytes = cli_max_bytes if cli_max_bytes is not None else cmd_max_bytes
    expected_backup_count = cli_backup_count if cli_backup_count is not None else cmd_backup_count
    expected = f"FILE:{expected_log_file}|MAX:{expected_max_bytes}|BACKUP:{expected_backup_count}"
    assert expected in res.output


@pytest.mark.parametrize(
    "cmd_log_file, cmd_max_bytes, cmd_backup_count, cli_log_file, cli_max_bytes, cli_backup_count",
    [
        # Nothing specified -> defaults
        (None, None, None, None, None, None),
        # Only @cli.cmd arguments -> they override the defaults
        ("cmd.log", 111, 1, None, None, None),
        # Only group CLI options -> they override the defaults
        (None, None, None, "cli.log", 222, 2),
        # CLI (on the group) overrides @cli.cmd
        ("cmd.log", 111, 1, "cli.log", 222, 2),
        # CLI wins where given, @cli.cmd fills the gaps
        ("cmd.log", 111, 1, "cli.log", None, None),
        ("cmd.log", 111, 1, None, 222, 2),
    ],
)
def test_log_file_options_precedence_with_group(
    tmp_path,
    cmd_log_file,
    cmd_max_bytes,
    cmd_backup_count,
    cli_log_file,
    cli_max_bytes,
    cli_backup_count,
):
    """Same precedence as `test_log_file_options_precedence`, but with the CLI options
    declared on the parent group instead of the command itself.
    """
    runner = CliRunner()

    cmd_kwargs: dict[str, Any] = {}
    if cmd_log_file is not None:
        cmd_kwargs["log_file"] = str(tmp_path / cmd_log_file)
    if cmd_max_bytes is not None:
        cmd_kwargs["log_file_max_bytes"] = cmd_max_bytes
    if cmd_backup_count is not None:
        cmd_kwargs["log_file_backup_count"] = cmd_backup_count

    group_args = []
    if cli_log_file is not None:
        group_args += ["--log-file", str(tmp_path / cli_log_file)]
    if cli_max_bytes is not None:
        group_args += ["--log-file-max-bytes", str(cli_max_bytes)]
    if cli_backup_count is not None:
        group_args += ["--log-file-backup-count", str(cli_backup_count)]

    @cli.grp()
    def main():
        pass

    @cli.cmd(grp=main, **cmd_kwargs)
    def sub(cfg: Config):
        print(f"FILE:{cfg.log_file}|MAX:{cfg.log_file_max_bytes}|BACKUP:{cfg.log_file_backup_count}")

    res = runner.invoke(main, [*group_args, "sub"])
    assert res.exit_code == 0

    expected_log_file = (
        str(tmp_path / (cli_log_file or cmd_log_file)) if (cli_log_file or cmd_log_file) else None
    )
    expected_max_bytes = cli_max_bytes if cli_max_bytes is not None else cmd_max_bytes
    expected_backup_count = cli_backup_count if cli_backup_count is not None else cmd_backup_count
    expected = f"FILE:{expected_log_file}|MAX:{expected_max_bytes}|BACKUP:{expected_backup_count}"
    assert expected in res.output


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


@pytest.mark.parametrize(
    "args, expected_exit, expected_output",
    [
        (["--numbers", "1, 2, 3"], 0, "Processed numbers: [1, 2, 3]"),
        (["--numbers", "1, two, 3"], 2, "Could not convert"),
        ([], 2, "Missing option"),
    ],
)
def test_list_of_int_conversion(args, expected_exit, expected_output):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")

    res = runner.invoke(process_numbers, args)
    assert res.exit_code == expected_exit
    assert expected_output in res.output


@pytest.mark.parametrize(
    "args, expected_exit, expected_output",
    [
        (["--values", "1.5, 2.5, 3.5"], 0, "Processed values: [1.5, 2.5, 3.5]"),
        (["--values", "1.5, two, 3.5"], 2, "Could not convert"),
        ([], 2, "Missing option"),
    ],
)
def test_list_of_float_conversion(args, expected_exit, expected_output):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--values", type=cli.types.ListOf(float), required=True)
    def process_values(values):
        print(f"Processed values: {values}")

    res = runner.invoke(process_values, args)
    assert res.exit_code == expected_exit
    assert expected_output in res.output


@pytest.mark.parametrize(
    "args, expected_exit, expected_output",
    [
        (["--words", "hello, world, test"], 0, "Processed words: ['hello', 'world', 'test']"),
        ([], 2, "Missing option"),
    ],
)
def test_list_of_str_conversion(args, expected_exit, expected_output):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--words", type=cli.types.ListOf(str), required=True)
    def process_words(words):
        print(f"Processed words: {words}")

    res = runner.invoke(process_words, args)
    assert res.exit_code == expected_exit
    assert expected_output in res.output


@pytest.mark.parametrize(
    "args, expected_exit, expected_output",
    [
        (["--numbers", "1, 2, 3"], 0, "Processed positive numbers: [1, 2, 3]"),
        (["--numbers", "-1, 2, 3"], 2, "failed verification"),
        ([], 2, "Missing option"),
    ],
)
def test_list_of_with_custom_verification(args, expected_exit, expected_output):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, verify=lambda x: x > 0), required=True)
    def process_positive_numbers(numbers):
        print(f"Processed positive numbers: {numbers}")

    res = runner.invoke(process_positive_numbers, args)
    assert res.exit_code == expected_exit
    assert expected_output in res.output


@pytest.mark.parametrize(
    "args, expected_exit, expected_output",
    [
        (["--numbers", "1, 2, 3"], 0, "Processed numbers: [1, 2, 3]"),
        (["--numbers", "1, 2, 3, 4, 5, 6"], 2, "Expected at most 5 elements"),
        (["--numbers", "1"], 2, "Expected at least 2 elements"),
        ([], 2, "Missing option"),
    ],
)
def test_list_of_with_length_constraints(args, expected_exit, expected_output):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, min_length=2, max_length=5), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")

    res = runner.invoke(process_numbers, args)
    assert res.exit_code == expected_exit
    assert expected_output in res.output


@pytest.mark.parametrize(
    "args, expected_exit, expected_output",
    [
        (["--numbers", "1, 2, 3"], 0, "Processed numbers: [1, 2, 3]"),
        (["--numbers", "1, 2"], 2, "Expected exactly 3 elements"),
        (["--numbers", "1, 2, 3, 4"], 2, "Expected exactly 3 elements"),
        ([], 2, "Missing option"),
    ],
)
def test_list_of_with_exact_length_constraint(args, expected_exit, expected_output):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, length=3), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")

    res = runner.invoke(process_numbers, args)
    assert res.exit_code == expected_exit
    assert expected_output in res.output


@pytest.mark.parametrize(
    "min_length, max_length, length, expected_exception",
    [
        (1, None, 3, 0),
        (1, 10, None, 0),
        (1, 5, 3, 1),
        (2, None, 4, 1),
        (2, 5, 2, 1),
    ],
)
def test_list_of_with_conflicting_length_constraints(min_length, max_length, length, expected_exception):
    if expected_exception:
        with pytest.raises(ValueError, match="Cannot specify both length and min/max length"):
            cli.types.ListOf(int, min_length=min_length, max_length=max_length, length=length)
    else:
        # Should not raise an exception
        cli.types.ListOf(int, min_length=min_length, max_length=max_length, length=length)


@pytest.mark.parametrize(
    "args, expected_args",
    [
        ([], []),
        (["--foo", "bar"], ["--foo", "bar"]),
        (["extra"], ["extra"]),
        (["--foo", "bar", "extra", "-x", "--baz", "1"], ["--foo", "bar", "extra", "-x", "--baz", "1"]),
    ],
)
def test_cmd_allow_extra_args(args, expected_args):
    runner = CliRunner()
    captured = []

    @cli.cmd(allow_extra_args=True)
    def main(lg: logging.Logger, ctx: cli.Context):
        captured.append(ctx.args)

    res = runner.invoke(main, args)
    assert res.exit_code == 0
    assert captured == [expected_args]


def test_cmd_allow_extra_args_logged_output():
    """The extra args should be reported in the logger output."""
    runner = CliRunner()

    @cli.cmd(allow_extra_args=True)
    def main(lg: logging.Logger, ctx: cli.Context):
        lg.info(ctx.args)

    res = runner.invoke(main, ["--foo", "bar"])
    assert res.exit_code == 0
    assert "['--foo', 'bar']" in res.output


@pytest.mark.parametrize(
    "args, expected_exit",
    [
        ([], 0),
        (["--foo", "bar"], 2),
        (["extra"], 2),
    ],
)
def test_cmd_allow_extra_args_default_false(args, expected_exit):
    runner = CliRunner()

    @cli.cmd()
    def main(lg: logging.Logger, ctx: cli.Context):
        lg.info(ctx.args)

    res = runner.invoke(main, args)
    assert res.exit_code == expected_exit


@pytest.mark.parametrize(
    "args, expected_args",
    [
        (["sub"], []),
        (["sub", "--foo", "bar"], ["--foo", "bar"]),
        (["sub", "--foo", "bar", "extra", "-x"], ["--foo", "bar", "extra", "-x"]),
    ],
)
def test_grp_allow_extra_args_propagates_to_subcommands(args, expected_args):
    runner = CliRunner()
    captured = []

    @cli.grp(allow_extra_args=True)
    def main():
        pass

    @cli.cmd(grp=main)
    def sub(lg: logging.Logger, ctx: cli.Context):
        captured.append(ctx.args)

    res = runner.invoke(main, args)
    assert res.exit_code == 0
    assert captured == [expected_args]


@pytest.mark.parametrize(
    "args, expected_exit",
    [
        (["sub"], 0),
        (["sub", "--foo", "bar"], 2),
        (["sub", "extra"], 2),
    ],
)
def test_grp_allow_extra_args_default_false(args, expected_exit):
    runner = CliRunner()

    @cli.grp()
    def main():
        pass

    @cli.cmd(grp=main)
    def sub(lg: logging.Logger, ctx: cli.Context):
        lg.info(ctx.args)

    res = runner.invoke(main, args)
    assert res.exit_code == expected_exit


def test_grp_allow_extra_args_opt_in_per_command():
    """A group with allow_extra_args=False must not prevent a subcommand from opting in."""
    runner = CliRunner()
    captured = []

    @cli.grp()
    def main():
        pass

    @cli.cmd(grp=main)
    def strict():
        print("STRICT OK")

    @cli.cmd(grp=main, allow_extra_args=True)
    def relaxed(lg: logging.Logger, ctx: cli.Context):
        captured.append(ctx.args)

    res = runner.invoke(main, ["strict", "--foo"])
    assert res.exit_code == 2

    res = runner.invoke(main, ["relaxed", "--foo", "bar"])
    assert res.exit_code == 0
    assert captured == [["--foo", "bar"]]


def test_grp_allow_extra_args_with_default_command():
    runner = CliRunner()
    captured = []

    @cli.cmd(allow_extra_args=True)
    def default_cmd(lg: logging.Logger, ctx: cli.Context):
        captured.append(ctx.args)

    @cli.grp(default=lambda: default_cmd, allow_extra_args=True)
    def main():
        pass

    main.add_command(default_cmd)

    res = runner.invoke(main, ["--foo", "bar"])
    assert res.exit_code == 0
    assert captured == [["--foo", "bar"]]


@pytest.fixture(
    params=[
        " ",  # space
        ";",  # semicolon
        "-",  # hyphen
        ".",  # single dot
        ":",  # colon
        "|",  # pipe
        "/",  # slash
        "\t",  # tab
        "::",  # multi-character separator
        "+",  # plus
    ]
)
def separator(request):
    """Separators commonly used to join/split list arguments on the CLI."""
    return request.param


def test_list_of_default_separator_is_comma():
    """`separator` defaults to a comma, so existing usages are unaffected."""
    sep = cli.types.ListOf(int).separator
    assert sep == ","

    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, separator=sep), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")

    res = runner.invoke(process_numbers, ["--numbers", sep.join(["1", "2", "3"])])
    assert res.exit_code == 0
    assert "Processed numbers: [1, 2, 3]" in res.output


def test_list_of_rejects_empty_separator():
    """An empty separator cannot be used to split a value, so reject it early."""
    with pytest.raises(ValueError, match="separator cannot be empty"):
        cli.types.ListOf(int, separator="")


def test_list_of_int_conversion_with_custom_separator(separator):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, separator=separator), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")
        print(f"Types: {[type(n).__name__ for n in numbers]}")

    res = runner.invoke(process_numbers, ["--numbers", separator.join(["1", "2", "3"])])
    assert res.exit_code == 0
    assert "Processed numbers: [1, 2, 3]" in res.output
    assert "Types: ['int', 'int', 'int']" in res.output


def test_list_of_float_conversion_with_custom_separator(separator):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--values", type=cli.types.ListOf(float, separator=separator), required=True)
    def process_values(values):
        print(f"Processed values: {values}")
        print(f"Types: {[type(v).__name__ for v in values]}")

    # Dot-free values so that the "." separator can be exercised as well.
    res = runner.invoke(process_values, ["--values", separator.join(["1", "2", "3"])])
    assert res.exit_code == 0
    assert "Processed values: [1.0, 2.0, 3.0]" in res.output
    assert "Types: ['float', 'float', 'float']" in res.output


def test_list_of_str_conversion_with_custom_separator(separator):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--words", type=cli.types.ListOf(str, separator=separator), required=True)
    def process_words(words):
        print(f"Processed words: {words}")

    res = runner.invoke(process_words, ["--words", separator.join(["hello", "world", "test"])])
    assert res.exit_code == 0
    assert "Processed words: ['hello', 'world', 'test']" in res.output


@pytest.mark.parametrize("separator", [";", "-", ".", ":", "|", "/", "\t", "::", "+"])
def test_list_of_custom_separator_strips_whitespace(separator):
    """Whitespace around elements is still stripped, whatever the separator is.

    The space separator is excluded: whitespace around it would produce empty parts.
    """
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, separator=separator), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")

    res = runner.invoke(process_numbers, ["--numbers", separator.join(["1", " 2", "3 "])])
    assert res.exit_code == 0
    assert "Processed numbers: [1, 2, 3]" in res.output


def test_list_of_custom_separator_does_not_split_on_comma(separator):
    """Only the configured separator splits the value, the comma becomes a regular character."""
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--words", type=cli.types.ListOf(str, separator=separator), required=True)
    def process_words(words):
        print(f"Processed words: {words}")

    res = runner.invoke(process_words, ["--words", f"hello,world{separator}test"])
    assert res.exit_code == 0
    assert "Processed words: ['hello,world', 'test']" in res.output


def test_list_of_custom_separator_conversion_failure(separator):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, separator=separator), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")

    res = runner.invoke(process_numbers, ["--numbers", separator.join(["1", "two", "3"])])
    assert res.exit_code == 2
    assert "Could not convert" in res.output


def test_list_of_custom_separator_with_verification(separator):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt(
        "--numbers",
        type=cli.types.ListOf(int, separator=separator, verify=lambda x: x > 0),
        required=True,
    )
    def process_positive_numbers(numbers):
        print(f"Processed positive numbers: {numbers}")

    res = runner.invoke(process_positive_numbers, ["--numbers", separator.join(["1", "2", "3"])])
    assert res.exit_code == 0
    assert "Processed positive numbers: [1, 2, 3]" in res.output

    res = runner.invoke(process_positive_numbers, ["--numbers", separator.join(["1", "0", "3"])])
    assert res.exit_code == 2
    assert "failed verification" in res.output


def test_list_of_custom_separator_with_length_constraints(separator):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt("--numbers", type=cli.types.ListOf(int, separator=separator, length=3), required=True)
    def process_numbers(numbers):
        print(f"Processed numbers: {numbers}")

    res = runner.invoke(process_numbers, ["--numbers", separator.join(["1", "2", "3"])])
    assert res.exit_code == 0
    assert "Processed numbers: [1, 2, 3]" in res.output

    res = runner.invoke(process_numbers, ["--numbers", separator.join(["1", "2"])])
    assert res.exit_code == 2
    assert "Expected exactly 3 elements, got 2" in res.output


def test_list_of_custom_separator_with_click_param_type(separator):
    runner = CliRunner()

    @cli.cmd()
    @cli.opt(
        "--values",
        type=cli.types.ListOf(cli.types.IntRange(min=0, max=10), separator=separator),
        required=True,
    )
    def process_values(values):
        print(f"Processed values: {values}")

    res = runner.invoke(process_values, ["--values", separator.join(["1", "2", "3"])])
    assert res.exit_code == 0
    assert "Processed values: [1, 2, 3]" in res.output

    res = runner.invoke(process_values, ["--values", separator.join(["1", "20"])])
    assert res.exit_code == 2
    assert "20 is not in the range" in res.output
