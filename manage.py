#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from infra.ops_cli import (
    build_pyd,
    eod,
    hotfix_verify,
    layer_boundaries,
    new_session,
    pin_processes,
    run_pytest,
    start_all,
    start_all_task,
    start_backend,
    validate_session,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Option_v4 Windows operations CLI")
    subparsers = parser.add_subparsers(dest="command")

    new_session.build_parser(subparsers)
    validate_session.build_parser(subparsers)
    run_pytest.build_parser(subparsers)
    start_backend.build_parser(subparsers)
    start_all.build_parser(subparsers)
    start_all_task.build_parser(subparsers)
    build_pyd.build_parser(subparsers)
    layer_boundaries.build_parser(subparsers)
    eod.build_parser(subparsers)
    hotfix_verify.build_parser(subparsers)
    pin_processes.build_parser(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
