# server/

Standalone edge / reverse-proxy configs for the static export. Prefer these when you want nginx or Envoy outside the Docker Compose / k8s stacks under `infra/global/`.

| Directory | Role |
| --- | --- |
| [`nginx/`](nginx/) | nginx main + vhost configs for serving `out/` (or reverse-proxying) |
| [`proxy/`](proxy/) | Envoy bootstrap YAMLs for an L7 reverse proxy in front of an origin |

Pick one edge process — do not run nginx and Envoy both bound to the same host port.
