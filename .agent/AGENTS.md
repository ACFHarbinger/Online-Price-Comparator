# AGENTS.md - Instructions for Coding Assistant LLMs

[![C++](https://img.shields.io/badge/C%2B%2B-17-00599C?logo=cplusplus&logoColor=white)](https://isocpp.org/)
[![CMake](https://img.shields.io/badge/CMake-Build-064F8C?logo=cmake&logoColor=white)](https://cmake.org/)

> **Version**: 1.0
> **Last Updated**: 2026-08-06
> **Purpose**: Authoritative reference for AI assistants (Claude, GPT, Gemini, Copilot, etc.) working in repositories generated from this template.

## Table of Contents

1. [Project Overview & Mission](#1-project-overview--mission)
2. [Technical Stack & Governance](#2-technical-stack--governance)
3. [Module Boundaries](#3-module-boundaries)
4. [Key CLI Entry Points](#4-key-cli-entry-points)
5. [Coding Standards](#5-coding-standards)
6. [Known Constraints](#6-known-constraints)

## 1. Project Overview & Mission

`Python-Module-Template` is a GitHub template repository designed for single-module C++ projects. It provides modern C++ scaffolding including CMake build configurations, GoogleTest unit testing, Google Benchmark micro-benchmarks, CI/CD pipelines, containerized dev environments, pre-commit hooks, and LLM coding-agent instructions.

## 2. Technical Stack & Governance

| Component | Specification | Notes |
| --- | --- | --- |
| C++ | C++17 | Standardized modern C++ language standard |
| Build System | CMake 3.20+ | Root `CMakeLists.txt` builds libraries, executables, tests, benchmarks |
| Unit Testing | GoogleTest 1.15+ | Integrated via `FetchContent` / `find_package` |
| Benchmarks | Google Benchmark 1.9+ | Integrated via `FetchContent` / `find_package` |
| Task Runner | Just | Command recipes in `justfile` and `tools/` |
| Config | `.env` / `config/` | JSON / environment configuration |

## 3. Module Boundaries

- `include/single_module_template/` — Public C++ header files.
- `src/` — Implementation files (`.cpp`).
- `test/` — Unit tests using GoogleTest.
- `benchmark/` — Performance micro-benchmarks using Google Benchmark.
- `config/` — Configuration assets (`default.json`).

## 4. Key CLI Entry Points

| Command | Purpose |
| --- | --- |
| `just --list` | List all available command-runner recipes |
| `just build` | Build the C++ module via CMake |
| `just test` | Run GoogleTest suite via CTest |
| `just bench` | Run Google Benchmark suite |
| `just lint` | Check formatting via `clang-format` |
| `just docs` | Build the MkDocs documentation site |

## 5. Coding Standards

- Follow C++ core guidelines and rules specified in `.agent/rules/cpp.md`.
- Prefer small, reviewable diffs. Do not reformat files unrelated to the change.
- Every new public header function/class must include documentation comments.
- Every new feature must include corresponding unit tests in `test/`.

## 6. Known Constraints

- Requires C++17 compliant compiler (GCC 9+, Clang 10+, MSVC 2019+).
- CMake 3.20 or later required.
