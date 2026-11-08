#!/usr/bin/env python3
"""
check_subdomains.py — Check which subdomains from a list are live (responding).

For each subdomain it:
  1. Tries DNS resolution.
  2. Tries an HTTP/HTTPS request and records the status code.

Usage:
    python3 check_subdomains.py subdomains.txt
    cat subdomains.txt | python3 check_subdomains.py
    python3 check_subdomains.py subdomains.txt --timeout 5 --workers 50 --output results.csv

Input file: one subdomain (or URL) per line. Blank lines and lines starting
with '#' are ignored.
"""

import argparse
import concurrent.futures
import csv
import socket
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


def normalize(host):
    """Strip scheme/path so we are left with just the hostname."""
    host = host.strip()
    if not host:
        return None
    if "://" in host:
        host = urlparse(host).netloc or urlparse(host).path
    return host.split("/")[0].strip()


def resolves(host):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


def probe_http(host, timeout):
    """Try https first, then http. Return (scheme, status, final_url) or None."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # we only care about liveness, not cert validity
    for scheme in ("https", "http"):
        url = f"{scheme}://{host}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "subdomain-liveness-checker"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return scheme, r.status, r.url
        except urllib.error.HTTPError as e:
            # Server responded (e.g. 403/404/500) — that still counts as live.
            return scheme, e.code, url
        except Exception:
            continue
    return None


def check(host, timeout):
    host = normalize(host)
    if not host:
        return None
    ip = resolves(host)
    if ip is None:
        return {"host": host, "status": "DEAD", "ip": "", "code": "",
                "scheme": "", "final_url": "", "note": "DNS did not resolve"}

    http = probe_http(host, timeout)
    if http is None:
        return {"host": host, "status": "RESOLVES", "ip": ip, "code": "",
                "scheme": "", "final_url": "", "note": "Resolves but no HTTP/HTTPS response"}

    scheme, code, final_url = http
    return {"host": host, "status": "LIVE", "ip": ip, "code": code,
            "scheme": scheme, "final_url": final_url, "note": ""}


def read_hosts(path):
    stream = sys.stdin if path in (None, "-") else open(path)
    with stream as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                yield line


def main():
    ap = argparse.ArgumentParser(description="Check which subdomains are live.")
    ap.add_argument("file", nargs="?", default="-",
                    help="File with one subdomain per line (default: stdin).")
    ap.add_argument("--timeout", type=float, default=5, help="Request timeout (s).")
    ap.add_argument("--workers", type=int, default=30, help="Concurrent checks.")
    ap.add_argument("--output", help="Optional CSV output path.")
    args = ap.parse_args()

    hosts = list(read_hosts(args.file))
    if not hosts:
        print("No subdomains to check.", file=sys.stderr)
        sys.exit(1)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(check, h, args.timeout): h for h in hosts}
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            if res is None:
                continue
            results.append(res)
            icon = {"LIVE": "[+]", "RESOLVES": "[~]", "DEAD": "[-]"}[res["status"]]
            detail = f'{res["scheme"]} {res["code"]}'.strip() or res["note"]
            print(f'{icon} {res["host"]:<40} {res["status"]:<9} {detail}')

    live = sum(1 for r in results if r["status"] == "LIVE")
    print(f"\nSummary: {live} live / {len(results)} checked", file=sys.stderr)

    if args.output:
        with open(args.output, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["host", "status", "ip", "code",
                                              "scheme", "final_url", "note"])
            w.writeheader()
            w.writerows(results)
        print(f"Saved CSV to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
