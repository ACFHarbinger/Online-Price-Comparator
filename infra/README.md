# infra/

Infrastructure-as-code and edge configs for `Python-Module-Template`.

| Directory | Scope | Purpose |
| --- | --- | --- |
| [`global/`](global/) | External / public-facing | Deploy & host tooling (docker, k8s, helm, terraform, ansible) |
| [`private/`](private/) | Internal / developer-only | Local developer tooling (e.g. webpack, wordpress) |
| [`cloud/`](cloud/) | Managed cloud hosts | AWS / Azure / Firebase / Serverless configs |
| [`server/`](server/) | Edge / reverse-proxy | Standalone nginx and Envoy configs |

## global/ (external)

| Directory | What it does |
| --- | --- |
| `global/docker/` | Build + run via Docker Compose |
| `global/k8s/` | Kubernetes manifests (base + overlays) |
| `global/helm/` | Helm chart wrapping the k8s manifests |
| `global/terraform/` | Cloud provisioning |
| `global/ansible/` | Host configuration playbooks |

## cloud/

Managed static/cloud deploy configs (when present): `aws/`, `azure-pipelines/`, `firebase/`, `serverless/`.

## private/ (internal)

Developer-only experiments (when present): `webpack/`, `wordpress/`.

## server/

| Directory | What it does |
| --- | --- |
| `server/nginx/` | Standalone nginx reverse-proxy / static site configs |
| `server/proxy/` | Envoy proxy configs |
