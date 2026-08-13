@echo off
REM post-commit.bat -- Windows equivalent of git/hooks/post-commit.
REM Verifies the just-made commit references a ticket ID and, if so,
REM best-effort transitions that ticket's board status. Fails open: always
REM exits 0, since post-commit cannot un-make a commit that already happened.

setlocal

for /f "delims=" %%R in ('git rev-parse --show-toplevel 2^>nul') do set REPO_ROOT=%%R
if "%REPO_ROOT%"=="" exit /b 0

set CHECK_SCRIPT=%REPO_ROOT%\git\scripts\check_commit_ref.py
set COMMIT_MSG_FILE=%REPO_ROOT%\.git\COMMIT_EDITMSG

if not exist "%CHECK_SCRIPT%" (
  echo post-commit: check_commit_ref.py not found, skipping 1>&2
  exit /b 0
)

where uv >nul 2>nul
if errorlevel 1 (
  echo post-commit: uv not found on PATH, skipping ticket check 1>&2
  exit /b 0
)

REM check_commit_ref.py imports agent_tools via a relative import, so it must
REM run as the git.scripts package (cwd at the repo root) rather than as a
REM bare script.
pushd "%REPO_ROOT%"
uv run python -m git.scripts.check_commit_ref --commit-msg-file "%COMMIT_MSG_FILE%"
if errorlevel 1 (
  echo post-commit: ticket reference check reported an issue ^(non-blocking^) 1>&2
)
popd

exit /b 0
