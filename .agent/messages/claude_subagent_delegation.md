---
### SUBAGENT DELEGATION PROTOCOL: CLAUDE

**Identity & Capability:**
You can deploy a Claude AI subagent via the local terminal using the `claude` CLI command. Claude is a stateless worker that excels at deep refactoring, nuanced code generation, and complex technical writing.

**When to Delegate:**
Invoke the Claude subagent for:
*   **Deep Refactoring:** Managing strict memory constraints or borrow-checker rules in Rust or C++.
*   **UI/Frontend Generation:** Generating structured code for complex layouts (e.g., TypeScript/React/Tauri dashboards).
*   **Granular Code Review:** Performing rigorous audits of custom algorithms or FFmpeg/OpenCV binding logic.

**Execution Syntax:**
Run the command in your shell, wrapping the prompt in strong quotes.
`claude 'YOUR_COMPREHENSIVE_PROMPT_HERE'`

**Subagent Prompting Rules (How to talk to Claude):**
1.  **Complete Independence:** Claude cannot read your memory. You MUST provide the exact code block or exact error logs it needs to act upon.
2.  **ReAct / CoT Triggers:** Instruct Claude to use `<thinking>` XML blocks to plan its refactoring steps before outputting code.
3.  **Strict Boundaries:** Specify exact input and output formats (e.g., "Output ONLY valid Rust code inside a single markdown block").

**Example Usage:**
`claude 'Act as an expert computer vision engineer. Refactor the following Rust OpenCV bindings used for stitching digital anime images (not camera photos) into a continuous panorama. Ensure memory safety and optimize the feature matching step. Wrap your reasoning in <thinking> tags, then provide the refactored code. Code to refactor: [INSERT_CODE_HERE]'`

**Failure Modes to Avoid:**
*   **Do not** include single quotes inside the prompt string without escaping them.
*   **Do not** delegate tasks that require multi-turn conversational context.
---