# Skill: Debug a Crash

1. Get a reliable repro command and the full crash output (stack trace, exit code, core dump if native code).
2. For native modules (rust/, cpp/), rebuild with debug symbols and reproduce under a debugger (`lldb`/`gdb`) or `rust-gdb`.
3. For managed runtimes (python/, typescript/, kotlin/, java/, go/), capture the full traceback — do not summarize it.
4. Bisect via `git bisect` if the crash is a regression against a known-good commit.
5. Once fixed, add a regression test that would have caught it, and note the root cause in the commit message.
