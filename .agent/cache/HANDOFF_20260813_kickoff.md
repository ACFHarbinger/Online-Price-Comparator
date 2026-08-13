# Handoff: Online Price Comparator — kickoff + hardware context

**Date**: 2026-08-13
**From**: Claude (session in `Coding-Assistants`, pkhunter's multi-agent Hub app repo)
**Why this file exists**: pkhunter is starting a brand-new session with you in *this* repo
(`Online-Price-Comparator`) right after a long session in an unrelated project
(`Coding-Assistants`). That other session hit a real hardware failure that
affects *this* machine generally, not just that repo — read section 1 before
running anything, including `pytest`.

---

## 1. Machine-wide hardware constraint (read this first)

**The CPU's cooling has failed and can trip a hard crash or a full desktop
logout under surprisingly light sustained load.** This isn't specific to
`Coding-Assistants` — it applies to any CPU-heavy work on this machine,
including this repo's test suite.

### What was actually measured (today, same machine)
- CPU: Intel i9-12900KS. `sensors` showed the package hitting **100°C
  (its critical/throttle limit) within ~5 seconds** of a trivial,
  single-instruction CPU load (`yes > /dev/null` across all 24 threads — not
  even a real compute workload).
- Confirmed via RAPL power-limit capping (`/sys/class/powercap/intel-rapl/...`,
  PL1=90W/PL2=125W) that this is **not** a runaway power-draw problem: actual
  measured power during a burn was ~97W (the cap *was* being enforced by the
  hardware) and it *still* hit 96–100°C. That level of thermal failure at that
  little power points at the cooler barely making contact with the die
  (dried-out/pumped-out paste, lost mounting pressure, or — if it's an AIO —
  a dead pump), not something fixable in software.
- Empirically isolated in this exact session: `cargo build` (no test code
  compiled) was safe every time. `cargo test` — even filtered to 5 trivial
  tests, even with `--test-threads=1`, even when the binary was already fully
  compiled and cached (`--no-run` and `--list` both succeeded first) — still
  triggered a crash/logout on repeated attempts. The tests themselves were
  checked line-by-line and are not heavy; the honest conclusion is the system
  is thermally marginal enough that *any* additional CPU burst — build, test
  execution, whatever — has a real, roughly random chance of tipping it over,
  not that test execution specifically is worse than build.
- Separately (and now resolved, so not a live concern): a chunk of *earlier*
  crashes/logouts today were actually caused by a rogue background service
  (`openclaw-gateway`, a personal autonomous-agent tool pkhunter had
  installed) sending a real session-logout, misdiagnosed for a while as more
  thermal instability before the actual cause was found in `journalctl` and
  purged. That's fixed and unrelated going forward — flagging only so you
  don't rediscover it as a live issue.

### What's already been done as a stopgap
- RAPL power cap applied (90W sustained / 125W burst) — reduces load
  slightly, does **not** fix the underlying contact-loss problem, and did
  **not** prevent the test-execution crashes described above. Treat it as
  "slightly safer than nothing," not "safe."
- A lightweight systemd user timer logs CPU/GPU temps + top processes every
  30s to `~/.local/share/systemd-monitor/logs/health-YYYY-MM-DD.log` — useful
  if you need to check whether a crash you just caused was thermal (rising
  temps in the last snapshot or two before a gap in the log) vs. something
  else. `systemctl --user status system-health-snapshot.timer` to confirm
  it's still running.

### The real fix, already ordered, not yet installed
pkhunter has purchased an **AMD Ryzen 9 9950X3D** + **MSI MPG X870E Carbon
WiFi** to replace the failing 12900KS/board entirely. Until that's physically
installed, the constraint above is still live.

**Interim update (same day, after the above was written):** pkhunter placed
a large external fan next to the case, and reports it "seems to have
somewhat helped." No burn-test/`sensors` data has been collected with the
fan in place yet to confirm by how much, so treat this as a partial,
unverified improvement, not a resolved problem — still ask before running
the test suite, and still expect a real (if perhaps now lower) chance of a
crash under sustained load until the actual hardware swap happens.

### What this means for you, working in this repo
- **Do not run `pytest`/`just test`/anything that executes the test suite**
  without pkhunter's explicit go-ahead for that specific run, given the crash
  risk is real and roughly random regardless of how light the tests look.
- Prefer verification that doesn't execute code under load: `ruff check`,
  `mypy`, `python -m py_compile`, `pytest --collect-only` (discovery only,
  no execution — this was proven safe on the Rust side via the equivalent
  `cargo test --list`, same principle should hold here).
- If a test run is genuinely necessary, ask first, then keep it as small and
  short as possible (a single test file/function, not the full suite), and
  be prepared for the session to end abruptly mid-command with no output —
  that's a crash, not a bug in what you ran.
- If pkhunter tells you the new CPU/motherboard is installed, this entire
  section is stale — ask for confirmation and drop these precautions.

---

## 2. What this repo actually needs to become

`Online-Price-Comparator` was just scaffolded from `Python-Module-Template`
(everything timestamped today, `pyproject.toml` still literally says
`name = "python-module-template"`) and has **no product-specific code yet** —
`src/` only has the template's placeholder `main.py`/`utils.py`/`core.py`/
`cli.py`. You're building this from scratch.

**The tool, in pkhunter's own words:** search the web for a product's
keywords, then produce a dashboard with:
- the product's links (across the multiple sites the search finds it on)
- a descriptive image of the product
- price statistics charts/plots comparing:
  - the price across multiple websites (a snapshot comparison), **and**
  - each site's own historical price over time

### Things worth thinking through before writing code (ask pkhunter if unclear)
- **Historical prices per site** implies the tool needs to persist what it
  finds over multiple runs (a local DB, most simply SQLite given no infra
  beyond this template) and accumulate a price history — a single one-shot
  run can't show a trend. Confirm whether pkhunter wants this to run
  on-demand and just build history passively over time, or wants an explicit
  scheduled/repeated-run mode from day one.
- **Web search / scraping approach**: raw scraping of arbitrary e-commerce
  sites is fragile and has real ToS/legal considerations per site. Worth
  asking whether pkhunter wants a specific fixed set of target sites (more
  robust, purpose-built scrapers/parsers), a general web-search API (e.g. an
  LLM-accessible search tool, SerpAPI-style, or Google/Bing Shopping APIs) to
  discover listings dynamically, or a mix.
- **Dashboard tech**: the template has no frontend/dashboard tooling
  preinstalled. Candidates worth raising: Streamlit or Dash (fast to stand
  up, Python-native, good for charts), a static HTML report generated per
  run (simplest, no server), or something heavier if pkhunter wants
  persistence/interactivity beyond a single report. Ask before committing to
  one.
- **Charting library**: nothing is in `pyproject.toml` yet — Plotly and
  matplotlib are the obvious candidates; Plotly pairs naturally with
  Streamlit/Dash if that's the dashboard direction.
- **Rate limiting / politeness**: any scraping needs sane rate limits and a
  real User-Agent policy; ask if pkhunter has specific sites in mind so this
  can be scoped concretely rather than guessed at.

### Template conventions already in place (from `Python-Module-Template`)
- Package manager: `uv` (`uv sync`, `uv run ...`). Task runner: `just`
  (`just --list` for available recipes — note the `justfile`/`tools/*/justfile`
  recipes were written for the *generic* template and may need edits for
  this project's actual dependencies).
- Lint/type-check: `ruff` (line-length 88, `select = ["E","F","I","B","UP","SIM","RUF"]`)
  and `mypy --strict`. Both configured in `pyproject.toml` already.
- Tests: `pytest`, configured via `[tool.pytest.ini_options]` in
  `pyproject.toml` (`testpaths = ["test"]`, coverage on by default via
  `addopts = "-v --cov=src --cov-report=term-missing"`) — remember section 1
  before running these for real.
- Layout: `src/<package>/` per-module dirs each with their own `__init__.py`
  + `py.typed` (the template's own convention — `src/core/`, `src/cli/`,
  `src/utils/` currently, all placeholders). `test/` mirrors it
  (`test_core.py`, `test_cli.py`, `test_utils.py`, `test_main.py`,
  `conftest.py`).
- **`.agent/AGENTS.md` is stale/wrong for this project** — it describes a
  C++/CMake/GoogleTest stack (copy-pasted from a sibling C++ variant of the
  template and never adapted for the Python variant). The real stack is what
  `pyproject.toml` actually says: Python/uv/pytest/ruff/mypy. Don't follow
  AGENTS.md's C++ instructions; worth fixing eventually but not urgent.
- `pyproject.toml`'s `name`, `description`, `[project.scripts]` entry point,
  and `README.md` all still say "python-module-template" / describe the
  generic template — will need renaming to reflect this project once real
  work starts.

---

## 3. Suggested first steps for the new session

1. Read this file, then ask pkhunter the open design questions in section 2
   before writing code — this project has real architecture decisions
   (scraping approach, dashboard tech, historical-price persistence model)
   that are pkhunter's to make, not yours to assume.
2. Rename the template identifiers (`pyproject.toml` `name`/`description`,
   `README.md`) to actually describe this project once scope is confirmed.
3. Treat section 1 as binding until pkhunter says otherwise.

No code has been written for the actual product yet — you're starting clean.
