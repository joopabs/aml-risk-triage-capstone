# Optional Step 8: local scoring service image. Build from the repository root:
#   docker build -t aml-triage-api -f deployment/Dockerfile --build-arg MODEL_VERSION=$(cat models/LATEST) .
# The bundle's pipeline.joblib is regenerated locally by `make pipeline` and is never committed.
FROM python:3.11-slim
ARG MODEL_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AML_MODELS_DIR=/app/models OMP_NUM_THREADS=2
WORKDIR /app
COPY requirements.txt requirements-api.txt pyproject.toml README.md LICENSE ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt
COPY src ./src
COPY configs ./configs
RUN pip install --no-cache-dir --no-deps -e .
COPY models/${MODEL_VERSION} ./models/${MODEL_VERSION}
RUN echo "${MODEL_VERSION}" > /app/models/LATEST
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
CMD ["uvicorn", "aml_triage.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
