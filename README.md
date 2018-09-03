These are the spec tests for TOML used by @iarna/toml.

The errors folder contains TOML files that should cause a parser to report an error.

The values folder contains TOML files and paired YAML or JSON files.  The
YAML files should parse to a structure that's deeply equal to the TOML
structure.  The JSON files match the patterns found in [BurntSushi 0.4 TOML
tests](https://github.com/BurntSushi/toml-test#json-encoding).

