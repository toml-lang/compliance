# Interfaces

For a decoder (AKA parser) or encoder (AKA writer) to be compatible with the provided runner, they must satisfy the interface described here.

They are executed in a subprocess, with additional details described below.

## Decoders

- Accept a TOML data on stdin until EOF.
- For invalid TOML data:
  - Return with a non-zero exit code.
- For valid TOML data:
  - Output a [JSON encoding](json-encoding.md) of the TOML data, to stdout.
  - Return with a zero exit code.

Decoders are run with all `.toml` files, with their output checked against the corresponding `.json` file (if it exists).

## Encoders

- Accept JSON data on stdin until EOF.
- For JSON data that cannot be converted to a valid TOML representation:
  - Return with a non-zero exit code.
- For JSON data that can be converted to a valid TOML representation:
  - Output a TOML representation of input, to stdout.
  - Return with a zero exit code.

Encoders are run with all `.json` files, with their output checked using a decoder and compared to the same `.json` file. The JSON input to a encoder is the same as, the JSON output of a decoder for the corresponding `.toml` file.
