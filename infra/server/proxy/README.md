# proxy/ (Envoy)

Envoy reverse-proxy configs for putting an L7 edge in front of the static export origin (typically nginx from `infra/server/nginx` or `infra/global/docker`).

## Files

| Path | Purpose |
| --- | --- |
| `envoy.yaml` | Reverse proxy on `:8080` → origin on `host.docker.internal:8081` |
| `envoy.static.yaml` | Same pattern documented for a local `serve` origin |

Admin interface listens on `:9901` (`/stats`, `/config_dump`).

## Quick start

Terminal 1 — origin (static files):

```bash
npm run build
npx --yes serve@latest out -l 8081
```

Terminal 2 — Envoy edge:

```bash
docker run --rm -p 8080:8080 -p 9901:9901 \
  --add-host=host.docker.internal:host-gateway \
  -v "$PWD/infra/server/proxy/envoy.yaml:/etc/envoy/envoy.yaml:ro" \
  envoyproxy/envoy:v1.31-latest -c /etc/envoy/envoy.yaml
```

Visit `http://localhost:8080`. Edit the cluster `socket_address` in `envoy.yaml` if the origin is not on the Docker host port 8081.
