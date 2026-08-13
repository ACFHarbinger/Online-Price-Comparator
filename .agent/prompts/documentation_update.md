# Prompt: Documentation Update

Given a request to update documentation:

1. Identify every doc surface affected: `README.md`, `docs/*.md`, `.agent/AGENTS.md`, inline docstrings/doc-comments.
2. Match the existing tone and structure of the surrounding document — don't introduce a new format for one section.
3. Verify code examples actually run against the current codebase before including them.
4. Update the table of contents/navigation (`docs/mkdocs.yml`) if a page was added, removed, or renamed.
5. Check for now-stale links elsewhere in the repo that reference the changed section.
