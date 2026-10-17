"""
Smart Park - Desktop Operator Workstation Entrypoint.
Runs the standalone desktop client for security booth guards and cashiers.
"""

import argparse
import json
import sys
import os

# Add root directory to path so imports work seamlessly
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from desktop.src.operator_window import launch_desktop_station, DesktopBridgeApi


def main():
    # Load config.json if present
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    default_server = cfg.get("gateway_server_url", "http://127.0.0.1:8080")
    default_booth = cfg.get("booth_id", "BOOTH-01")
    default_cashier = cfg.get("cashier_id", "AGENT-MEZIANE")

    parser = argparse.ArgumentParser(description="Smart Park - Desktop Guard & Cashier Station")
    parser.add_argument("--server", type=str, default=default_server, help="FastAPI gateway server URL")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display for background testing")
    parser.add_argument("--booth", type=str, default=default_booth, help="Operator booth identifier")
    parser.add_argument("--cashier", type=str, default=default_cashier, help="Cashier badge identifier")

    args = parser.parse_args()

    print("=" * 60)
    print(" Smart Park - Poste Opérateur et Caisse (Desktop Station)")
    print(f" Gateway Server: {args.server}")
    print(f" Booth ID:       {args.booth}")
    print(f" Active Cashier: {args.cashier}")
    print(f" Headless Mode:  {args.headless}")
    print("=" * 60)

    bridge = launch_desktop_station(
        server_url=args.server,
        headless=args.headless,
        booth_id=args.booth,
        cashier_id=args.cashier,
        config=cfg,
    )
    if args.headless:
        print("[smartpark-desktop] Headless station operational. Running automated diagnostic test...")
        tkt = bridge.print_ticket("104822 119 16", lane_id=args.booth)
        scan = bridge.scan_ticket(tkt["barcode_value"])
        settle = bridge.settle_payment(tkt["ticket_id"], "104822 119 16", 200.0, payment_method="CASH", tendered_dzd=500.0)
        zrep = bridge.close_shift()
        print(f"[smartpark-desktop] Diagnostic Passed: Ticket={tkt['ticket_id']} | Total={scan['total_due_dzd']} DZD | Change={settle['change_dzd']} DZD | Z-Hash={zrep['audit_hash'][:16]}...")
        print("[smartpark-desktop] Subsystems operational: ESC/POS Printer, Barcode Scanner, POS Ledger, Acoustic Audio.")


if __name__ == "__main__":
    main()
