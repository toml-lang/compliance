#!/usr/bin/env python
"""TOML compliance suite runner.
"""

import argparse
import difflib
import json
import multiprocessing
import os
import subprocess
import sys
import textwrap
from pathlib import Path


_LATEST_VERSION = "v1.0.0-rc1"
_ALL_VERSIONS = ["v0.4", "v1.0.0-rc1"]

class Failed(Exception):
    """Raised when a check fails for some reason

    :param reason:
        Textual reason, explaining why the test failed.
    :param cause:
        Exception, representing the reason for failure.
    :param diff:
        A tuple of 2 JSON-able objects, that should be presented as a diff.
    """

    def __init__(self, reason, *, cause=None, diff=None):
        self.reason = reason

        if cause is not None:
            self.details = repr(cause)
        elif diff is not None:
            correct, got = diff
            correct_str = json.dumps(correct, indent=2, sort_keys=True)
            got_str = json.dumps(got, indent=2, sort_keys=True)

            diff_lines = difflib.ndiff(
                correct_str.splitlines(keepends=False),
                got_str.splitlines(keepends=False),
            )
            self.details = "\n".join(diff_lines)
        else:
            self.details = None

        super().__init__(reason, self.details)


# --------------------------------------------------------------------------------------
# Colors
# --------------------------------------------------------------------------------------
_COLOR_ALLOWED = sys.stdout.isatty()
# Handle optional Windows-ANSI support dependency (colorama)
if _COLOR_ALLOWED and os.name == "nt":
    try:
        import colorama
    except ImportError:
        print(
            "TIP: If you install https://pypi.org/project/colorama, this program "
            "will look much better."
        )
        _COLOR_ALLOWED = False
    else:
        colorama.init()

_COLOR_NAMES = ["grey", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
_COLOR_DICT = dict(zip(_COLOR_NAMES, range(8)))


def colored(s, *, fg=None, bg=None, bold=False):
    assert fg is not None or bg is not None
    if not _COLOR_ALLOWED:
        return s

    ansi_codes = []
    if bold:
        ansi_codes.append(1)
    if fg is not None:
        ansi_codes.append(_COLOR_DICT[fg] + 30)
    if bg is not None:
        ansi_codes.append(_COLOR_DICT[bg] + 40)

    parameters = ";".join(map(str, ansi_codes))

    return f"\033[{parameters}m{s}\033[0m"


# --------------------------------------------------------------------------------------
# Filesystem interaction
# --------------------------------------------------------------------------------------
all_tests_dir = Path(__file__).parent / "tests"


def ensure_executable(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Could not find file: {path}")
    if not os.access(path, os.X_OK):
        raise PermissionError(f"Not an executable file: {path}")


def _locate_test_pairs(tests_dir):
    for path in (tests_dir / "invalid").glob("*.toml"):
        yield path, None
    for path in (tests_dir / "invalid").glob("*.json"):
        yield None, path

    for path in (tests_dir / "valid").glob("*.toml"):
        json_equivalent = path.with_suffix(".json")
        assert json_equivalent.exists(), f"Missing: {json_equivalent}"
        yield path, json_equivalent


def _filter_based_on_markers(pairs, markers):
    def marker_filter(pair):
        # No filtering if no markers given.
        if not markers:
            return True

        for m in markers:
            # Matches the name of the file (allows -m array)
            if m in pair[0].stem:
                return True
            # Matches the name of the parent folder (allows -m invalid)
            if m == pair[0].parent.name:
                return True
        return False

    yield from filter(marker_filter, pairs)


def get_test_pairs(version, markers):
    test_dir = all_tests_dir / version
    pairs = _locate_test_pairs(test_dir)
    yield from _filter_based_on_markers(pairs, markers)


# --------------------------------------------------------------------------------------
# Input / Output Handling
# --------------------------------------------------------------------------------------
def run_program(program, *, stdin, clean_exit):
    try:
        process = subprocess.run(
            [program], input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError as error:
        raise Failed(f"could not run: {program}", cause=error)

    # For invalid Test Cases
    if clean_exit:
        if process.returncode:
            raise Failed(f"Got a non-zero exit code: {process.returncode}")
        if process.stderr:
            raise Failed(f"Got stderr output!", cause=process.stderr)
    else:
        if not process.returncode:
            raise Failed("Should have rejected input.")

    return process.stdout


def load_json(*, content, source):
    assert source in ["decoder's output", "test case input"]
    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise Failed(f"Could not parse {source} JSON", cause=error)

    # TODO: validation and normalization?


# --------------------------------------------------------------------------------------
# Actual Compliance Checks
# --------------------------------------------------------------------------------------
def test_decoder(toml_file, json_file, clean_exit, decoder):
    content = run_program(decoder, stdin=toml_file.read_bytes(), clean_exit=clean_exit)

    # For valid Test Cases
    correct_json = load_json(content=json_file.read_text(), source="test case input")
    decoded_json = load_json(content=content, source="decoder's output")

    if correct_json != decoded_json:
        raise Failed(
            "Mismatch between expected JSON and decoded JSON.",
            diff=(correct_json, decoded_json),
        )


def test_encoder(json_file, clean_exit, encoder, decoder):
    input_json = load_json(content=json_file.read_text(), source="test case input")

    # Encode the input.
    result = run_program(encoder, stdin=json_file.read_bytes(), clean_exit=clean_exit)

    # Decode the result.
    decoded = run_program(decoder, stdin=result, clean_exit=True)

    # Check round-trip was same as original
    round_trip_json = load_json(content=decoded, source="decoder's output")

    if input_json != round_trip_json:
        raise Failed(
            "Mismatch between original JSON and encoded-decoded JSON.",
            diff=(input_json, round_trip_json),
        )


# --------------------------------------------------------------------------------------
# Check Runners!
# --------------------------------------------------------------------------------------
def _show_summary(counts):
    total = sum(counts.values())
    if total == 0:
        print(colored("No tests were selected!", fg="red"))
        return

    n_passed = colored(
        f"{counts['pass']} passed", fg="green" if counts["pass"] else "red"
    )
    n_total = f"{total} total"

    print()
    print("Summary: ", n_passed, ", ", n_total, sep="")


def _show_pass(name):
    print(colored(" PASS ", fg="grey", bg="green"), end=" ")
    print(colored(name, fg="cyan"))


def _show_fail(name, failed):
    print(colored(" FAIL ", fg="grey", bg="red"), end=" ")
    print(colored(name, fg="cyan"))

    reason = textwrap.indent(failed.reason, "  ")
    print(colored(reason, fg="red"))
    if failed.details:
        print(textwrap.indent(str(failed.details), "    "))


# Those messy functions above, keeps this function clean.
def run_with_reporting(function, checks):
    counts = {"fail": 0, "pass": 0}

    for name, kwargs in checks:
        try:
            function(**kwargs)
        except Failed as e:
            _show_fail(name, e)
            counts["fail"] += 1
        else:
            _show_pass(name)
            counts["pass"] += 1

    _show_summary(counts)

    # This will be the program's exit code
    if counts["fail"] or sum(counts.values()) == 0:
        return 1
    return 0


def encoder_compliance(encoder, decoder, version, markers):
    def generate_parameters():
        for toml_file, json_file in get_test_pairs(version, markers):
            if json_file is None:  # need something to encode!
                continue
            yield (
                json_file,
                {
                    "json_file": json_file,
                    "clean_exit": toml_file is not None,
                    "encoder": encoder,
                    "decoder": decoder,
                },
            )

    ensure_executable(encoder)
    ensure_executable(decoder)

    return run_with_reporting(test_encoder, generate_parameters())


def decoder_compliance(decoder, version, markers):
    def generate_parameters():
        for toml_file, json_file in get_test_pairs(version, markers):
            if toml_file is None:  # need something to decode!
                continue
            yield (
                toml_file,
                {
                    "toml_file": toml_file,
                    "clean_exit": json_file is not None,
                    "json_file": json_file,
                    "decoder": decoder,
                },
            )

    ensure_executable(decoder)
    return run_with_reporting(test_decoder, generate_parameters())


# --------------------------------------------------------------------------------------
# CLI argument handling
# --------------------------------------------------------------------------------------
def get_parser():
    parser = argparse.ArgumentParser(prog="toml-compliance/run.py", allow_abbrev=False)
    subparsers = parser.add_subparsers(title="commands")

    encoder = subparsers.add_parser("encoder")
    encoder.add_argument("target", action="store", help="Encoder to test")
    encoder.add_argument(
        "--decoder",
        action="store",
        help="Supporting decoder for testing",
        required=True,
    )
    encoder.add_argument(
        "-m",
        metavar="MARKER",
        dest="markers",
        help="Only run tests that match given marker. Can be specified multiple times.",
        nargs=1,
    )
    encoder.add_argument(
        "--version",
        default=f"{_LATEST_VERSION}",
        dest="version",
        help=f"""
             TOML version to use for tests.
             Default is version \"{_LATEST_VERSION}\"""",
        choices=_ALL_VERSIONS,
    )

    decoder = subparsers.add_parser("decoder")
    decoder.add_argument("target", action="store", help="Encoder to test")
    decoder.add_argument(
        "-m",
        metavar="MARKER",
        dest="markers",
        help="Only run tests that match given marker. Can be specified multiple times.",
        nargs=1,
    )
    decoder.add_argument(
        "--version",
        default=f"{_LATEST_VERSION}",
        choices=_ALL_VERSIONS,
        dest="version",
        help=f"""
             TOML version to use for tests.
             Default is version \"{_LATEST_VERSION}\"""",
    )

    return parser


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    if "target" not in args:
        parser.print_help()
        sys.exit(1)

    # This check isn't super clear at first glance. It works since the 'decoder'
    # subparser does not have a 'decoder' argument.
    should_run_encoder_tests = "decoder" in args

    if should_run_encoder_tests:
        exit_code = encoder_compliance(args.target, args.decoder, args.version, args.markers)
    else:
        exit_code = decoder_compliance(args.target, args.version, args.markers)

    sys.exit(exit_code)
