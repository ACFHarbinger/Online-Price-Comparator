# nginx/

Standalone nginx configs for serving the Next.js static export (`out/`), as an alternative to the docker-compose stack under `infra/global/docker/`.

## Files

| Path | Purpose |
| --- | --- |
| `nginx.conf` | Main process config (gzip, logging, includes `conf.d/`) |
| `conf.d/app.conf` | Virtual host: static export + Next.js `try_files` fallback |
| `conf.d/reverse-proxy.conf.example` | Sample reverse-proxy vhost in front of an upstream |

## Quick start (container)

```bash
npm run build
docker run --rm -p 8080:80 \
  -v "$PWD/out:/usr/share/nginx/html:ro" \
  -v "$PWD/infra/server/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$PWD/infra/server/nginx/conf.d:/etc/nginx/conf.d:ro" \
  nginx:1.27-alpine
```

Visit `http://localhost:8080`. For the the static/app origin `basePath`, open `http://localhost:8080/app/` after the postbuild symlink exists, or serve from a root that already includes that prefix.
