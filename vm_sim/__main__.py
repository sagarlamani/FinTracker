"""CLI runner for the two-VM connection simulation."""

from __future__ import annotations

import argparse
import sys

from .simulator import Simulation


def _banner() -> None:
    print(
        """
╔══════════════════════════════════════════════════════════╗
║         Two-VM Network Connection Simulation             ║
║                                                          ║
║   alpha (10.0.0.1)  ←── vnet0 ──→  beta (10.0.0.2)     ║
╚══════════════════════════════════════════════════════════╝
"""
    )


def _print_result(result) -> None:
    print("\n── Scenario Steps ──────────────────────────────────────")
    for step in result.steps:
        print(f"  {step.index}. [{step.actor:6}] {step.title}")
        print(f"           {step.description}")

    print("\n── Packet Trace ────────────────────────────────────────")
    for i, pkt in enumerate(result.packets, 1):
        print(f"  {i:02d}. {pkt.summary()}")

    print("\n── VM Alpha Log ────────────────────────────────────────")
    for line in result.vm_a_log:
        print(f"  {line}")

    print("\n── VM Beta Log ─────────────────────────────────────────")
    for line in result.vm_b_log:
        print(f"  {line}")

    print("\n── Messages Delivered ──────────────────────────────────")
    if result.messages_delivered:
        for msg in result.messages_delivered:
            print(f"  • {msg!r}")
    else:
        print("  (none)")

    print("\n── Result ──────────────────────────────────────────────")
    status = "SUCCESS" if result.success else "FAILED"
    print(f"  {status}: {result.summary}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Simulate two virtual machines connecting over a virtual LAN"
    )
    parser.add_argument(
        "--latency",
        type=float,
        default=2.0,
        help="Network latency in milliseconds (default: 2.0)",
    )
    parser.add_argument(
        "--msg-a",
        default="Hello from Alpha VM!",
        help="Message from alpha to beta",
    )
    parser.add_argument(
        "--msg-b",
        default="Hello from Beta VM!",
        help="Message from beta to alpha",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="TCP listen port on beta (default: 8080)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the final summary",
    )
    args = parser.parse_args(argv)

    if not args.quiet:
        _banner()

    sim = Simulation(
        latency_ms=args.latency,
        message_a_to_b=args.msg_a,
        message_b_to_a=args.msg_b,
        listen_port=args.port,
    )
    result = sim.run()

    if args.quiet:
        status = "OK" if result.success else "FAIL"
        print(f"{status}: {result.summary}")
    else:
        _print_result(result)

    sim.shutdown()
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
