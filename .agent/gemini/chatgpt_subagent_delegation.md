---
### SUBAGENT DELEGATION PROTOCOL: CHATGPT

**Identity & Capability:**
You are equipped to launch a ChatGPT AI subagent via the `chatgpt` command. ChatGPT executes statelessly and has no awareness of this current chat session.

**When to Delegate:**
Invoke the ChatGPT subagent for:
*   **Algorithm Conceptualization:** Designing evolutionary operators or Contextual Multi-Armed Bandit (CMAB) reward logic.
*   **Documentation & Abstraction:** Generating clear, high-level summaries of complex system state machines or behavioral trees.
*   **Alternative Paradigms:** Asking for a completely different approach to a problem when current models are stuck in local optima.

**Execution Syntax:**
Execute the command in your terminal environment. Always enclose the prompt in single quotes.
`chatgpt 'YOUR_COMPREHENSIVE_PROMPT_HERE'`

**Subagent Prompting Rules (How to talk to ChatGPT):**
1.  **Context Injection:** Paste all relevant snippets and constraints into the prompt.
2.  **Structured Output:** Use the Template Pattern. Define exactly how the output should look using a mock structure.
3.  **Chain-of-Thought:** For complex logic, explicitly ask ChatGPT to "Think step-by-step before providing the final answer."

**Example Usage:**
`chatgpt 'Act as a Reinforcement Learning specialist. I need to design a reward function for a hierarchical RL model managing daily waste collection routing. Think step-by-step about how to balance route efficiency with temporal constraints. Output format: 
## Reasoning: [Step-by-step thoughts]
## Reward Function Logic: [Bullet points]'`

**Failure Modes to Avoid:**
*   **Do not** nest quotes improperly (e.g., `chatgpt 'He said 'hello''`).
*   **Do not** use ambiguous instructions; be explicit about the domain.
---