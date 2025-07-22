import argparse
import json
from flask_app import hlf_client


def main():
    parser = argparse.ArgumentParser(description="Inspect blockchain blocks")
    parser.add_argument(
        "--info", action="store_true", help="print ledger height and current hash"
    )
    parser.add_argument("--block", type=int, help="fetch a specific block number")
    args = parser.parse_args()

    if args.info:
        info = hlf_client.query_blockchain_info()
        print("Height:", info["height"])
        print("Current Hash:", info["current_hash"])

    if args.block is not None:
        block = hlf_client.get_block(args.block)
        print(json.dumps(block, indent=2))


if __name__ == "__main__":
    main()
