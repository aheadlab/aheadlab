FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/home/app/.cache/huggingface OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
WORKDIR /app
ARG INSTALL_MODEL=false
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY . .
RUN python -m pip install -e . && if [ "$INSTALL_MODEL" = "true" ]; then python -m pip install 'torch>=2.4' --index-url https://download.pytorch.org/whl/cpu && python -m pip install -r requirements-model.txt; fi
RUN useradd --create-home app && mkdir -p /home/app/.cache/huggingface && chown -R app:app /app /home/app/.cache
USER app
EXPOSE 8501
CMD ["sh", "-c", "streamlit run app/streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
