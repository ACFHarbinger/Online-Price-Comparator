# C++ Rules

- Target C++17, built via CMake. Format with `clang-format` (project `.clang-format` config); never hand-format against it.
- Prefer RAII and smart pointers (`std::unique_ptr`/`std::shared_ptr`) over raw `new`/`delete`.
- Headers go in `cpp/include/`, implementation in `cpp/src/`. Keep the public header surface minimal and documented with Doxygen comments.
- Tests live under `cpp/test/` using GoogleTest/Catch2, registered with CTest.
- Benchmarks live under `cpp/benchmark/` using Google Benchmark.
- When exposing C++ to another language (Python via `pybind11`, etc.), keep the binding layer thin — it should translate types, not contain logic.
