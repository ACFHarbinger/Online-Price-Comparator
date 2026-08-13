# Prompt: Generate a CLI Command

Given a request for a new CLI command:

1. Identify the target language module and its existing CLI framework (e.g. `argparse`/`typer` for Python, `cobra` for Go, `clap` for Rust).
2. Match the existing command's argument/flag naming conventions.
3. Provide `--help` text and at least one usage example in the command's docstring.
4. Add a test invoking the command and asserting on its output/exit code.
5. Document the new command in the relevant `docs/` page.
