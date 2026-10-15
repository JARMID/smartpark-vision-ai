"""
SmartPark Vision AI - Desktop Operator Workstation Entrypoint.
Runs the standalone desktop client for security booth guards and cashiers.
"""

import argparse
import sys
import os

# Add root directory to path so imports work seamlessly
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from desktop.src.operator_window import launch_desktop_station, DesktopBridgeApi


def main():
    parser = argparse.ArgumentParser(description="SmartPark Vision AI - Desktop Guard & Cashier Station")
    parser.add_argument("--server", type=str, default="http://127.0.0.1:8080", help="FastAPI gateway server URL")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display for background testing")
    parser.add_argument("--booth", type=str, default="BOOTH-01", help="Operator booth identifier")
    parser.add_argument("--cashier", type=str, default="AGENT-MEZIANE", help="Cashier badge identifier")

    args = parser.parse_args()

    print("=" * 60)
    print(" SmartPark Vision AI - Desktop Operator Station")
    print(f" Gateway Server: {args.server}")
    print(f" Booth ID:       {args.booth}")
    print(f" Active Cashier: {args.cashier}")
    print(f" Headless Mode:  {args.headless}")
    print("=" * 60)

    bridge = launch_desktop_station(server_url=args.server, headless=args.headless)
    if args.headless:
        print("[smartpark-desktop] Headless station operational. Press Ctrl+C to terminate.")


if __name__ == "__main__":
    main()
