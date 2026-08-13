---
### SUBAGENT DELEGATION PROTOCOL: GROK

**Identity & Capability:**
You can deploy a Grok AI subagent via the local terminal using the `grok` CLI command (Grok Build by xAI). Grok is a tool-using coding agent that can explore codebases, edit files, run shell commands, and implement multi-step software engineering tasks. It does not share your context window; treat it as an independent worker.

**When to Delegate:**
Invoke the Grok subagent for:
*   **End-to-End Implementation:** Building features, fixing bugs, or applying multi-file refactors with tests and commits.
*   **Codebase Exploration:** Navigating large repositories, tracing call graphs, and summarizing architecture before you act.
*   **Agentic Tool Work:** Tasks that benefit from iterative shell/build/test loops rather than pure text generation.
*   **Real-Time / Web-Aware Reasoning:** Problems that need up-to-date context, search, or alternative high-level approaches when you are stuck.

**Execution Syntax:**
Run the command in your shell, wrapping the prompt in strong quotes to prevent shell evaluation errors. Prefer single-turn / headless mode so the subagent prints a result and exits:
`grok -p 'YOUR_COMPREHENSIVE_PROMPT_HERE'`

For longer agentic work that may need tools and multiple turns:
`grok --always-approve -p 'YOUR_COMPREHENSIVE_PROMPT_HERE'`

**Subagent Prompting Rules (How to talk to Grok):**
1.  **Complete Independence:** Grok does not see your conversation. Include paths, constraints, acceptance criteria, and any required snippets or error logs in the prompt.
2.  **Actionable Scope:** State the working directory, which files may change, and what "done" looks like (e.g., "tests pass", "output only the diff summary").
3.  **Strict Boundaries:** Specify format and limits (e.g., "Do not open a PR", "Output ONLY a bullet list of findings", "Modify only files under src/").

**Example Usage:**
`grok -p 'Act as an expert systems engineer. In the current repository, locate the authentication middleware, identify why refresh tokens are rejected after 24h, and propose a minimal fix. Constraints: 1. Do not modify files. 2. Return a short root-cause analysis and a concrete patch suggestion in a single markdown code block.'`

**Failure Modes to Avoid:**
*   **Do not** use unescaped single quotes inside the `grok` command string.
*   **Do not** assume Grok knows your prior conversation or unstated project goals.
*   **Do not** nest quotes improperly (e.g., `grok -p 'He said 'hello''`).
---
