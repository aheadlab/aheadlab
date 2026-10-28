"""Explicit UCI acquisition and content-validated, all-sheet Excel cache."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

import pandas as pd
import requests

URL = 'https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip'
FILENAME = 'online_retail_II.xlsx'
RAW = Path('data/raw') / FILENAME
OUT = Path('data/processed/transazioni.parquet')


def download_uci(destination=RAW):
    destination = Path(destination)
    response = requests.get(URL, timeout=180)
    response.raise_for_status()
    with ZipFile(BytesIO(response.content)) as archive:
        matches = [info for info in archive.infolist() if info.filename == FILENAME]
        if len(matches) != 1 or matches[0].file_size > 300_000_000:
            raise ValueError('Missing, duplicate or oversized official Excel member')
        # Never extract archive paths: write only the exact expected member.
        content = archive.read(matches[0])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination


def source_fingerprint(raw=RAW):
    return hashlib.sha256(Path(raw).read_bytes()).hexdigest()


def converti_una_volta(raw=RAW, out=OUT):
    raw, out = Path(raw), Path(out)
    digest = source_fingerprint(raw)
    manifest = out.with_suffix('.json')
    identity = {'sha256': digest, 'source': str(raw.resolve()), 'schema': 1}
    if out.exists() and manifest.exists():
        try:
            if json.loads(manifest.read_text()) == identity:
                return pd.read_parquet(out)
        except (ValueError, OSError):
            pass
    sheets = pd.read_excel(raw, sheet_name=None)
    frame = pd.concat(sheets.values(), ignore_index=True)
    frame.columns = frame.columns.str.strip()
    # Excel mixes numeric and string invoice identifiers; parquet needs a stable type.
    for col in ['Invoice', 'InvoiceNo', 'StockCode', 'Description', 'Country']:
        if col in frame:
            frame[col] = frame[col].astype('string')
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix('.tmp.parquet')
    frame.to_parquet(temporary, index=False)
    temporary.replace(out)
    manifest.write_text(json.dumps(identity), encoding='utf-8')
    return frame
