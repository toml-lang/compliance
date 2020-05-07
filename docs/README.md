# Using toml-compliance

Hello there! If you're reading this, you're likely implementing/maintain a TOML parser/writer (or... you're a really curious person! go you!). Thank you for your interest in TOML!

For using this compliance test suite, to test a TOML decoder / encoder, a [specific interface](interfaces.md) to them needs to be provided. This interface (and test files themselves) utilize a [JSON encoding](json-encoding.md) of TOML documents.

## Usage

> NOTE: If you're not able to use the provided runner for some technical reason, consider filing an issue. You can write your own test runner obviously, but that might be more work than necessary.

`run.py` is the main entry point. It runs the provided programs using the interface described above, against various test cases, while reporting progress and providing information about failures.

### Requirements

You'll need Python 3.6+ to use this test runner. There are no additional dependencies for the test runner.

On Windows, you may (optionally) install [colorama](https://pypi.org/project/colorama) in the environment you run this script from, to get colored output.

### Running

For running tests on a decoder, run:

```sh-session
$ python run.py decoder <your-decoder>
```

For running tests on an encoder, run:

```sh-session
$ python run.py encoder <your-encoder> --decoder <your-decoder>
```

The encoder tests require a specification-compliant decoder. The encoder's output is validated by decoding it, and checking if that is equivalent to the original input.

### Markers

For both these commands, `-m` can be used to provide "markers" which are used to filter tests based on their category (`valid` or `invalid`) or names (good choices would be `array`, `table`, `unicode`). You may provide this option multiple times. A few examples:

```sh-session
# run for all valid decoder tests
$ python run.py decoder <your-decoder> -m valid
# run for all invalid decoder tests, with "array" in their name
$ python run.py decoder <your-decoder> -m array -m invalid
# run for all decoder tests, with "table" in their name
$ python run.py decoder <your-decoder> -m table
```

## Test Layout

There are 2 kinds of tests in this repository: valid and invalid.

Valid tests check that a decoder (AKA parser) accepts valid TOML documents, and an encoder represents data correctly as TOML. Each valid tests consists of two files -- a `.toml` file containing a valid TOML document and a `.json` file containing the JSON encoding of that document.

Invalid tests check that a decoder rejects invalid TOML data, and an encoder rejects data that can not be represented as TOML. An invalid test consist of a single `.toml` file (invalid TOML data, decoder) or a single `.json` file (invalid JSON encoding, encoder).

The tests should be small enough that writing the JSON encoding by hand will not give you brain damage. The exact reverse is true when testing encoders.

### Naming

Every test file should be named after the fault it is trying to expose, and ideally, each test should try to test one thing and one thing only. The names of the tests can be used as "markers" to select them, so these names should contain as much relevant context as necessary.
