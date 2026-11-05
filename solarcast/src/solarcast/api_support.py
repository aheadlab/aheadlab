"""Local HTTP utilities; copied per repository to keep deployments independent."""
from contextlib import contextmanager
from datetime import date, datetime
import json
import logging
import math
from pathlib import Path
from threading import BoundedSemaphore

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)
_gate = BoundedSemaphore(1)


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def response(value):
    return JSONResponse(clean(value))


@contextmanager
def calculation():
    if not _gate.acquire(blocking=False):
        raise HTTPException(409, 'Un calcolo è già in corso. Riprova tra poco.')
    try:
        yield
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(503, 'Dati locali non disponibili. Consulta la guida per prepararli.') from None
    except (ImportError, OSError, RuntimeError):
        raise HTTPException(503, 'Modello o servizio non disponibile. Verifica installazione, cache e rete.') from None
    except (ValueError, KeyError):
        raise HTTPException(400, 'Dati o parametri incompatibili con il calcolo richiesto.') from None
    except Exception:
        logger.error('Forecast failed; sensitive upstream details omitted')
        raise HTTPException(503, 'Calcolo non disponibile. Riprova o verifica i dati di origine.') from None
    finally:
        _gate.release()


def report_paths(root):
    result = {}
    if (root / 'metadata.json').is_file():
        result['baseline'] = root
    if root.is_dir():
        for path in sorted(root.iterdir()):
            if path.is_dir() and not path.is_symlink() and (path / 'metadata.json').is_file():
                result[path.name] = path
    return result


def install_common(app: FastAPI, name: str, root: Path):
    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'app': name}

    @app.get('/api/reports')
    def reports():
        return response({'reports': [dict(id=key, label=key, metadata=json.loads((path/'metadata.json').read_text()))
                                    for key, path in report_paths(root/'results').items()]})

    @app.get('/api/reports/{report_id}')
    def report(report_id: str):
        path = report_paths(root/'results').get(report_id)
        if path is None:
            raise HTTPException(404, 'Report non trovato')
        tables = {}
        for file in sorted(path.glob('*.csv')):
            if file.name not in {'inventario_giornaliero.csv', 'anomaly_days.csv'}:
                tables[file.stem] = pd.read_csv(file).to_dict('records')
        return response({'id': report_id, 'metadata': json.loads((path/'metadata.json').read_text()), 'tables': tables})


def install_frontend(app: FastAPI, root: Path):
    dist = root/'web'/'dist'
    if (dist/'assets').is_dir():
        app.mount('/assets', StaticFiles(directory=dist/'assets'), name='assets')

    @app.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        if path == 'api' or path.startswith('api/'):
            raise HTTPException(404, 'Endpoint non trovato')
        if not (dist/'index.html').is_file():
            raise HTTPException(503, 'Frontend non costruito. Esegui npm run build in web/.')
        return FileResponse(dist/'index.html')
