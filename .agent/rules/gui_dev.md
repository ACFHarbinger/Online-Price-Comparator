# GUI Development Rules

- Keep UI components presentation-only; business logic belongs in a service/store layer that the UI calls into, so it stays testable without a rendered UI.
- Every new interactive control needs a keyboard-accessible path and an accessible name/label — not just a mouse affordance.
- Long-running work (>100ms) must run off the UI thread (worker thread, async task, or backend call) with visible progress/cancellation.
- Match the existing design system/component library before introducing a new one-off style.
- Add at least one component/integration test per new screen or panel.
