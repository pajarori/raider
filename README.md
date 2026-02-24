<div align="center">

# raider

A domain priority scoring tool for bug bounty that helps decide what targets to hunt first.

![raider Demo](raider.gif)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/pajarori/raider?style=flat&logo=github)](https://github.com/pajarori/raider/stargazers)
[![Forks](https://img.shields.io/github/forks/pajarori/raider?style=flat&logo=github)](https://github.com/pajarori/raider/network/members)
[![Issues](https://img.shields.io/github/issues/pajarori/raider?style=flat&logo=github)](https://github.com/pajarori/raider/issues)
[![Last Commit](https://img.shields.io/github/last-commit/pajarori/raider?style=flat&logo=github)](https://github.com/pajarori/raider/commits/main)

</div>

## Installation

```bash
pipx install git+https://github.com/pajarori/raider.git
```

## Usage

```bash
# Check a single domain
raider -d example.com

# Check a list of domains from a file
raider -l domains.txt

# Stream domains via stdin
cat domains.txt | raider

# Check with custom threads
raider -l domains.txt -t 20

# Save output to a file (JSON, CSV, or TXT)
raider -l domains.txt -o results.json

# Output results as JSON to stdout (useful for piping)
raider -l domains.txt --json
```

### Options

| Flag | Description |
|------|-------------|
| `-d, --domain` | Target domain to check |
| `-l, --list` | File containing list of target domains |
| `-t, --threads` | Number of concurrent threads to use for scanning (default: 10) |
| `-o, --output` | Output file (.txt, .json, .csv) |
| `--json` | Output results as JSON to stdout |

## Output Notes

- `tier` shows the score tier (`high`, `medium`, `low`, `no data`)
- `confidence` shows provider coverage quality
- `providers` in `--json` output shows each provider value and normalized score (or `null` if unavailable)

## License

MIT License
