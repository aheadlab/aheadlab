FROM node:22-bookworm-slim AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/home/app/.cache/huggingface OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HF_HUB_OFFLINE=1
WORKDIR /project
ARG INSTALL_MODEL=false
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src/ ./src/
RUN python -m pip install -e .
RUN if [ "$INSTALL_MODEL" = "true" ]; then python -m pip install 'torch>=2.4' --index-url https://download.pytorch.org/whl/cpu && python -m pip install 'timestral @ git+https://github.com/mistralai/timestral.git@a534bdbd244d64f3d9d743f46c7bf6fc330ed4ff'; fi
COPY results/ ./results/
COPY docs/ ./docs/
COPY scripts/ ./scripts/
COPY --from=frontend /web/dist ./web/dist/
RUN useradd --create-home app && mkdir -p /home/app/.cache/huggingface && chown -R app:app /project /home/app/.cache
USER app
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/api/health', timeout=3)"
CMD ["python","-m","uvicorn","carbonshift.api:app","--host","0.0.0.0","--port","8501"]
