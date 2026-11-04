#!/usr/bin/env python3
"""HTTP health probe with latency threshold. Exit codes: 0 OK, 1 WARNING, 2 CRITICAL."""
import argparse
import sys
import time
import urllib.error
import urllib.request


def probe(url: str, timeout: float) -> tuple:
    """Return (status_code or None, elapsed_ms, error or None)."""
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, (time.perf_counter() - start) * 1000, None
    except urllib.error.HTTPError as e:
        return e.code, (time.perf_counter() - start) * 1000, None
    except Exception as e:  # DNS failure, refused, timeout, TLS error
        return None, (time.perf_counter() - start) * 1000, str(e)


def evaluate(status, elapsed_ms, error, max_ms):
    if error is not None or status is None or status >= 500:
        return 2, f"CRITICAL: {error or status}"
    if status >= 400:
        return 1, f"WARNING: HTTP {status}"
    if elapsed_ms > max_ms:
        return 1, f"WARNING: slow ({elapsed_ms:.0f} ms > {max_ms:.0f} ms)"
    return 0, f"OK: HTTP {status} in {elapsed_ms:.0f} ms"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url")
    p.add_argument("--timeout", type=float, default=5)
    p.add_argument("--max-ms", type=float, default=1000)
    a = p.parse_args()
    code, msg = evaluate(*probe(a.url, a.timeout), a.max_ms)
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
