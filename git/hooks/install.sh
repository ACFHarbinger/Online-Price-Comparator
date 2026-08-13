#!/usr/bin/env bash
#
# install.sh -- symlink git/hooks/* into .git/hooks/ so they actually run.
#
# `.git/hooks/` is local-only and untracked by design (git will not let a
# repo ship hooks that execute automatically on clone, for security
# reasons). This script is the one-time, explicit opt-in step a contributor
# runs to wire our tracked hooks into their local git.
#
# Usage:
#   bash git/hooks/install.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="${REPO_ROOT}/git/hooks"
HOOKS_DST="${REPO_ROOT}/.git/hooks"

for hook in pre-commit post-commit; do
  ln -sf "../../git/hooks/${hook}" "${HOOKS_DST}/${hook}"
  chmod +x "${HOOKS_SRC}/${hook}"
  echo "Linked ${hook} -> .git/hooks/${hook}"
done

echo "Done. Set PROJECT_ID and GITHUB_TOKEN in your shell env to enable live board updates from post-commit."
