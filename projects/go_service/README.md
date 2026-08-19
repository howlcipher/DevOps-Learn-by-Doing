# Go Service demo application

The Go-based learner-facing workload for the DevOps Learn by Doing curriculum. This is
a real, runnable Go HTTP application using only the standard library, separate from the platform's
own code in `src/devops_learn/`.

## Endpoints

- `GET /health` returns `{"status": "ok"}`.
- `GET /info` returns non-secret service metadata: name, version, environment.

## Configuration

Read from environment variables, all with sensible defaults:

- `SERVICE_NAME` (default `go-service`)
- `SERVICE_VERSION` (default `0.1.0`)
- `ENVIRONMENT` (default `development`)
- `PORT` (default `8000`)
- `WEATHER_API_KEY` (optional secret, never leaked in endpoints)

## Run it yourself

```
go run .
```

## Test it yourself

```
go test -v ./...
go vet ./...
```

## Container

Multi-stage build compiling a static Go binary in the builder stage and copying it into a minimal, non-root runtime image:

```
docker build -t go-service:dev .
docker run -p 8000:8000 go-service:dev
```
