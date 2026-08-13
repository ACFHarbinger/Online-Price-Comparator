# 1. Record architecture decisions

Date: 2026-07-30

## Status

Accepted

## Context

We need a lightweight way to record significant, hard-to-reverse technical decisions so future contributors (human or LLM agent) understand *why* the system looks the way it does, not just *what* it does.

## Decision

We will use Architecture Decision Records (ADRs), one per decision, numbered sequentially under `docs/adr/`, following the format described by [Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

## Consequences

- Every ADR is immutable once accepted; a reversal gets a new ADR that supersedes it, rather than editing history.
- `docs/ARCHITECTURE.md` links to relevant ADRs instead of re-explaining their reasoning.
