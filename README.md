# Subdomain Liveness Checker

A tiny, dependency-free Python script that takes a list of subdomains and tells
you which are **live**, which only **resolve** (DNS but no web server), and which
are **dead**. Standard library only — no `pip install` required.

## How it works

For each subdomain it:

1. Resolves DNS — if that fails, the host is `DEAD`.
2. Tries HTTPS then HTTP and records the status code. Any response (even
   `403`/`404`/`500`) counts as `LIVE`.

| State          | Meaning                                       |
| -------------- | --------------------------------------------- |
| `[+] LIVE`     | Responds over HTTP/HTTPS                       |
| `[~] RESOLVES` | DNS resolves but no web server answered       |
| `[-] DEAD`     | DNS did not resolve                           |

## Usage

```bash
python3 check_subdomains.py subdomains.txt
```

```bash
cat subdomains.txt | python3 check_subdomains.py --timeout 5 --workers 50 --output results.csv
```

Input is one subdomain (or URL) per line. Blank lines and lines starting with
`#` are ignored. Checks run concurrently (`--workers`, default 30), and
`--output` writes a CSV with IP, status code, and final redirect URL.

### Options

| Flag         | Default | Description                     |
| ------------ | ------- | ------------------------------- |
| `--timeout`  | `5`     | Per-request timeout in seconds  |
| `--workers`  | `30`    | Number of concurrent checks     |
| `--output`   | —       | Optional CSV output path        |

## Example

```
[+] github.com         LIVE   https 200
[+] www.google.com     LIVE   https 200
[-] nonexistent.xyz    DEAD   DNS did not resolve
Summary: 2 live / 3 checked
```

## Note

Only use this against domains you own or are explicitly authorized to test.
