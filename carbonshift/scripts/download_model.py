"""Explicit optional network step; never called by the web application."""
import os
os.environ['HF_HUB_OFFLINE']='0'
from huggingface_hub import snapshot_download
snapshot_download('mistralai/Timestral-5M',revision='bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f')
