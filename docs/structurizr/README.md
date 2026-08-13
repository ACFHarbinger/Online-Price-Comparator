# Structurizr C4 Model

Render locally with Structurizr Lite:

```bash
docker run -it --rm -p 8080:8080 \
  -v $(pwd)/docs/structurizr:/usr/local/structurizr \
  structurizr/lite
open http://localhost:8080
```

Export to Mermaid/PlantUML via the Structurizr CLI:

```bash
structurizr-cli export -workspace docs/structurizr/workspace.dsl \
  -format mermaid -output docs/structurizr/diagrams/
```

Edit [`workspace.dsl`](workspace.dsl) to update the model — it's the single source of truth for the Context/Container/Component diagrams referenced from [`../ARCHITECTURE.md`](../ARCHITECTURE.md).
