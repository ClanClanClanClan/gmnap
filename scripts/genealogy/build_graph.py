#!/usr/bin/env python3
import os, json, argparse, asyncio
from dotenv import load_dotenv

load_dotenv()

from src.pipeline.stage6_graph_consistency import populate_graph


async def main(entries_path: str, edges_path: str):
    with open(entries_path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    with open(edges_path, "r", encoding="utf-8") as f:
        edges = json.load(f)

    await populate_graph(entries=entries, edges=edges, compute_metrics=True, batch_size=1000)
    print("Graph population complete.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", required=True, help="JSON file with entries list")
    ap.add_argument("--edges", required=True, help="JSON file with edges list")
    args = ap.parse_args()
    asyncio.run(main(args.entries, args.edges))
