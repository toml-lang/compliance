# JSON Encoding

In this repository, `.json` files contain a JSON encoding of TOML data, as described below.

## Description

TOML tables encode to JSON Objects. TOML table arrays encode to JSON Array of Objects. TOML values are encoded as a JSON Object with the following structure:

```json
{
  "type": "<type>",
  "value": <value>
}
```

`<type>` is one of:

- `string`
- `integer`
- `float`
- `boolean`
- `offset datetime`
- `local datetime`
- `local date`
- `local time`
- `array`

When `<type>` is an `array`, the `<value>` is a JSON array containing equivalent JSON encoding of the values of the TOML array. In all other cases, `<value>` is a JSON String.

Note that the only JSON values ever used are Objects, Arrays and Strings.

## Example

```toml
best-day-ever = 1987-07-05T17:45:00Z

[number-theory]
boring = false
perfection = [6, 28, 496]
```

The JSON encoding for the above is:

```json
{
  "best-day-ever": {"type": "datetime", "value": "1987-07-05T17:45:00Z"},
  "number-theory": {
    "boring": {"type": "bool", "value": "false"},
    "perfection": {
      "type": "array",
      "value": [
        {"type": "integer", "value": "6"},
        {"type": "integer", "value": "28"},
        {"type": "integer", "value": "496"}
      ]
    }
  }
}
```

## Why JSON?

In order for a language agnostic test suite to work, we need some kind of data exchange format. TOML cannot be used, as it would imply that a particular parser has a blessing of correctness.

JSON is a simple, well-established data exchange format. Support for JSON parsing is included in the standard library of many popular languages, and there are excellent libraries for other languages.

The simplicity of JSON, however, creates a need for an encoding of TOML values (as described above). The explicit typing of TOML values in the JSON encoding is a good thing though, since it reduces the assumptions being made overall.
