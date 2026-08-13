---
### SUBAGENT DELEGATION PROTOCOL: GEMINI

**Identity & Capability:**
You have the ability to spawn an independent Gemini AI subagent via your local terminal using the `agy` CLI command. Gemini does not share your context window; it acts as a stateless, highly capable assistant. 

**When to Delegate:**
Invoke the Gemini subagent for:
*   **Alternative Reasoning:** Generating a second opinion on complex logic (e.g., operations research heuristics).
*   **Parallel Processing:** Delegating isolated sub-tasks (e.g., drafting a regex, summarizing a log file) while you focus on the main architecture.
*   **Data Pipeline/Optimization Insights:** Leveraging Gemini's strong capabilities in standardizing data transformations or generating boilerplate for complex data structures.

**Execution Syntax:**
Run the command in your shell, wrapping the prompt in strong quotes to prevent shell evaluation errors.
`agy 'YOUR_COMPREHENSIVE_PROMPT_HERE'`

**Subagent Prompting Rules (How to talk to Gemini):**
1.  **Zero-Shot Context:** You MUST include all necessary code, logs, or context in your string. Gemini cannot see your current workspace unless explicitly provided in the prompt.
2.  **Explicit Formatting:** Tell Gemini exactly how to output the response (e.g., "Return ONLY raw JSON," or "Provide a Markdown table").
3.  **Role Definition:** Assign Gemini a role if helpful (e.g., "Act as an expert Rust systems programmer...").

**Example Usage:**
`agy 'Act as an expert in combinatorial optimization. Review the following Python logic for a matheuristic routing solver and identify potential bottlenecks in the node selection phase. Return only a bulleted list of 3 specific optimizations: [INSERT_LOGIC_HERE]'`

**Failure Modes to Avoid:**
*   **Do not** use unescaped single quotes inside the `agy` command string.
*   **Do not** assume Gemini knows the history of our conversation.
*   **Do not** delegate tasks that require writing files directly, unless you instruct Gemini to output the exact terminal commands for you to run.
---