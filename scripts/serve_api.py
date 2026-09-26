#!/usr/bin/env python3
"""Run only the API locally; the frontend dev server proxies /api to it."""
from http.server import HTTPServer
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.adapter import ApiHandler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    server = HTTPServer(("127.0.0.1", args.port), ApiHandler)
    print(f"Local API: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
