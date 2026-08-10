# API Platform demo application

The learner-facing workload the DevOps Learn by Doing curriculum builds and operates. This is
a real, runnable FastAPI application, separate from the platform's own code in
`src/devops_learn/`.

## Endpoints

- `GET /health` returns `{"status": "ok"}`.
- `GET /info` returns non-secret service metadata: name, version, environment.

## Configuration

Read from environment variables, all with sensible defaults:

- `SERVICE_NAME` (default `api-platform`)
- `SERVICE_VERSION` (default `0.1.0`)
- `ENVIRONMENT` (default `development`)
- `PORT` (default `8000`)

## Run it yourself

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test it yourself

```
pip install -r requirements.txt httpx pytest
pytest
```

## Container

```
docker build -t api-platform:dev .
docker run -p 8000:8000 api-platform:dev
```
