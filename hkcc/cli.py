"""Console entry points for an installed hKCC.

``hkcc`` launches the Streamlit app against the bundled dataset; ``hkcc api``
serves the read API. Both work from any working directory, because the database
lives inside the package (see :data:`hkcc.db.config.DEFAULT_SQLITE_PATH`).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from hkcc.db.config import APP_VERSION, DEFAULT_SQLITE_PATH

APP_SCRIPT = Path(__file__).resolve().parent / "streamlit_app.py"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def proxy_settings() -> tuple[bool, str | None]:
    """Decide whether uvicorn may rewrite the peer address from proxy headers.

    uvicorn enables ``--proxy-headers`` by default, which replaces
    ``request.client`` with whatever ``X-Forwarded-For`` says. Since that header
    is written by the caller, honouring it on a directly-reachable service lets
    anyone reset their own rate-limit bucket by rotating the value. Proxy
    headers are therefore trusted only when the operator states how many
    reverse proxies sit in front, via ``HKCC_TRUSTED_PROXY_HOPS``.
    """
    if _env_int("HKCC_TRUSTED_PROXY_HOPS", 0) <= 0:
        return False, None
    return True, os.environ.get("HKCC_FORWARDED_ALLOW_IPS", "127.0.0.1")


def _run_app(args: argparse.Namespace) -> int:
    try:
        from streamlit.web import cli as stcli
    except ModuleNotFoundError:
        print("Streamlit is not installed. Install it with: pip install streamlit", file=sys.stderr)
        return 1

    sys.argv = [
        "streamlit",
        "run",
        str(APP_SCRIPT),
        "--server.port",
        str(args.port),
        "--server.address",
        args.address,
    ]
    return int(stcli.main() or 0)


def _run_api(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ModuleNotFoundError:
        print("uvicorn is not installed. Install it with: pip install 'uvicorn[standard]'", file=sys.stderr)
        return 1

    proxy_headers, allow_ips = proxy_settings()
    uvicorn.run(
        "hkcc.api.main:app",
        host=args.address,
        port=args.port,
        proxy_headers=proxy_headers,
        forwarded_allow_ips=allow_ips,
    )
    return 0


def _show_info(_: argparse.Namespace) -> int:
    print(f"hKCC {APP_VERSION}")
    print(f"dataset: {DEFAULT_SQLITE_PATH}")
    print(f"present: {DEFAULT_SQLITE_PATH.is_file()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hkcc", description="Key Characteristics of Human Carcinogens")
    parser.add_argument("--version", action="version", version=f"hkcc {APP_VERSION}")
    sub = parser.add_subparsers(dest="command")

    app_cmd = sub.add_parser("app", help="Run the Streamlit app (default)")
    app_cmd.add_argument("--port", type=int, default=8501)
    app_cmd.add_argument("--address", default="localhost")
    app_cmd.set_defaults(func=_run_app)

    api_cmd = sub.add_parser("api", help="Run the read API")
    api_cmd.add_argument("--port", type=int, default=8000)
    api_cmd.add_argument("--address", default="127.0.0.1")
    api_cmd.set_defaults(func=_run_api)

    info_cmd = sub.add_parser("info", help="Show version and dataset location")
    info_cmd.set_defaults(func=_show_info)

    # `hkcc` and `hkcc --port 8501` mean `hkcc app ...`; only an explicit
    # subcommand (or a top-level flag) skips that default.
    tokens = list(sys.argv[1:] if argv is None else argv)
    passthrough = {"app", "api", "info", "-h", "--help", "--version"}
    if not tokens or tokens[0] not in passthrough:
        tokens = ["app", *tokens]

    args = parser.parse_args(tokens)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
