# OEUF DNS

Map the DNS environment of a domain.

## Install

```bash
pip install -e .
```

## Usage

```bash
python -m src example.com                  # Basic scan
python -m src google.com -d 3              # Deeper scan
python -m src oracle.com -g                # + Generate graph image
python -m src se.com --no-blacklist        # Disable CDN/cloud filter
python -m src tf1.fr -e spotify facebook   # Add exclusions
```

### Options

| Option | Description |
|--------|-------------|
| `-d, --depth N` | Recursion depth (default: 2) |
| `-g, --graph` | Generate JPG graph image |
| `-e, --exclude` | Extra patterns to exclude |
| `-p, --parallel N` | Workers (default: 5) |
| `--no-blacklist` | Disable default blacklist |
| `-v, --verbose` | Verbose mode |

## Testing

```bash
python -m pytest tests/test.py
```

## Blacklist

`src/data/blacklist.txt` contains CDN/cloud patterns (cloudflare, aws, azure...).
Edit or use `--no-blacklist` to disable.

## License

MIT