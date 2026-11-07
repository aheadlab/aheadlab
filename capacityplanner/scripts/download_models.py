"""Explicitly download pinned weights, outside the web application's lifecycle."""
from huggingface_hub import snapshot_download
from capacityplanner.core import REVISIONS
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--size', choices=REVISIONS, default='5M')
args = parser.parse_args()
snapshot_download(f'mistralai/Timestral-{args.size}', revision=REVISIONS[args.size])
