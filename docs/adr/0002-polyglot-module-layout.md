# 2. One top-level directory per language

Date: 2026-07-30

## Status

Accepted

## Context

Projects generated from this template may combine multiple languages (Python for orchestration/ML, TypeScript for UI, Rust/C++/Go for performance-critical cores, Kotlin/Java for JVM/Android targets). Each language ecosystem expects its own dependency manifest and directory conventions.

## Decision

Each language gets exactly one top-level directory (`python/`, `typescript/`, `kotlin/`, `java/`, `rust/`, `go/`, `cpp/`) containing that language's dependency manifest plus `src/`, `test/`, `benchmark/`, and `config/`. Cross-language contracts live under `docs/` or a shared `schemas/` directory, never duplicated per module.

## Consequences

- CI, `.pre-commit-config.yaml`, and `justfile` recipes can all key off the top-level directory name to dispatch to the right toolchain.
- A project that doesn't need a given language simply deletes that directory.
