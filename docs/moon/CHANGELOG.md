# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Created templates and placeholder documents for research and reports directories under `docs/research/` and `docs/reports/`.
- Created a beautiful, interactive Vue documentation portal in `docs/website/` that parses and displays all repository documentation files dynamically with search, dark mode, alert styling, and navigation.
- Created `website/javascript/` workspace similar to the typescript/ directory but for JavaScript, and added it to root workspace settings and `justfile` tasks.
- Populated `langs/sql`, `langs/graphql`, `langs/mjml`, `r/`, and `ruby/` directories with comprehensive multi-language code snippets.
- Populated `website/html/` (with a premium dark-themed landing page), `website/php/`, and `website/css/` (with a modular CSS framework architecture).
- Populated all `libraries/` subdirectories (including Prisma ORM, Fastlane, Rails, LESS, SASS, SCSS, Stylus, Delta Lake, PHPMailer, Expo, Firebase, TensorFlow for `flow`, PyTorch for `torch`, and Jinja templates).
- Populated package manager configuration examples in the `env/` directory and its subdirectories (including Bower, Conda, C++ CMakeLists.txt/Qt GUI `.pro` files, Gopm, Gradle, Maven, NPM, Pixi, and UV configurations).
- Populated Jupyter notebook examples in `notebooks/` utilizing `notebook_setup.py` utility.
- Added editor settings templates for IntelliJ IDEA, Obsidian, and Sublime Text under the `settings/` directory.
- Initial template scaffolding: root files (`LICENSE`, `README.md`, `.env.example`, `.pre-commit-config.yaml`, `.gitignore`/`.gitattributes`), `.git/` CI/CD, `git/` (`CONTRIBUTING.md`, `codecov.yaml`), `docs/` documentation portal (MkDocs + Sphinx + Structurizr + ADRs), `moon/` roadmap and changelog.
- `.agent/` LLM coding-agent scaffolding: `AGENTS.md` plus generic rules, workflows, prompts, and skills covering all six supported languages.
- Six language module skeletons (`python/`, `typescript/`, `kotlin/`, `rust/`, `go/`, `cpp/`), root workspace orchestrator files, and merged `python/validation/` dev-tooling.
- `java/` Maven module (7th language), wired into CI/pre-commit/justfile/docs alongside the existing six.
- Root Gradle wrapper and multi-project build files pairing with the existing `settings.gradle.kts`.
- `docs/moon/roadmaps/developer_tools.md`: architecture plan for a polyglot `dev/` developer-assistant tool, synthesized from prior art across the org's other repos.
- GitHub Project (V2) backlog automation (`git/` + `.git/workflows/agent_sync.yml`).
- `infra/{k8s,helm,terraform,ansible}/` infra-as-code scaffolding, alongside the relocated `infra/docker/`.
- `dev/` developer-assistant tool, milestones D1–D5 of `docs/moon/roadmaps/developer_tools.md`: the `input/protobuf/codegraph.proto` schema, a hand-mirrored Python data model (`core/model.py`), a real AST-based Python import-graph parser (`input/python/parser.py`), multi-source graph aggregation (`core/aggregate.py`), layer classification + forbidden-direction violation detection (`core/layers.py`), Tarjan's-SCC circular-dependency detection (`core/cycles.py`), a self-contained vis.js/Jinja2 HTML report generator (`output/html/report.py`), and a `cli.py` tying it together (`report`/`check` subcommands). 13 passing pytest cases, including a fixture project with an intentional import cycle.

### Changed

- Moved `moon/` directory into `docs/` to integrate with the documentation portal, and updated all referencing files.
- Moved `docker/` to `infra/docker/` to make room for other infra-as-code stacks; updated all referencing files.

## [0.1.0] — 2026-07-30

### Added

- Repository created from scratch as a GitHub template.
