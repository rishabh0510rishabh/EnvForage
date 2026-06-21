# AI Usage Policy

> **Philosophy**: Deterministic logic > AI generation.

Because EnvForage generates executable scripts that modify a user's operating system, environment, and hardware drivers, we enforce strict boundaries on how Artificial Intelligence (LLMs) can be utilized within the platform.

This document outlines the allowed scope, restricted actions, and safety mechanisms for AI features.

---

## 1. Where AI is ALLOWED

AI is used as an **assistant** to help users understand their environment, not as the final decision-maker for system state.

### ✅ Explanations
LLMs are permitted to read `DiagnosticReport` JSON files and provide plain-english explanations of *why* an environment is broken (e.g., "Your CUDA version is 11.8, but PyTorch 2.4 requires CUDA 12.1 or 12.4").

### ✅ Troubleshooting Guidance
LLMs can suggest troubleshooting steps to the user in a chat interface or markdown report, provided those steps do not execute automatically.

### ✅ Template Customization
LLMs can be used to generate custom *additions* to a script (e.g., "Add a command to download my dataset from S3"), provided that the output is passed through the `SafetyFilter` and rendered via the Template Engine.

---

## 2. Where AI is PROHIBITED

To prevent hallucinations from causing system damage, AI is strictly forbidden from bypassing our core deterministic engines.

### ❌ Destructive Shell Commands
AI models are not permitted to generate raw shell commands that perform destructive actions. All AI output must pass through `SafetyFilter`, which strictly blocks `rm -rf`, `format`, `dd`, `DROP`, and others.

### ❌ Driver Deletion or Modification
AI must never generate scripts that uninstall NVIDIA/AMD drivers, modify kernel parameters, or change boot configurations.

### ❌ Filesystem Cleanup
AI cannot be given tools or permissions to automatically "clean up" directories, wipe user folders, or delete system caches.

### ❌ Package Version Guessing
AI **must not** be used to guess compatible package versions. All version resolution must be executed strictly by the deterministic `CompatibilityEngine` using the hardcoded matrix. AI may only read the output of the Compatibility Engine, not replace it.

---

## 3. Hallucination Prevention Rules

When an LLM is used (e.g., in Phase 4: AI Troubleshooting Layer):

1. **Structured Input**: The LLM is provided with validated `DiagnosticReport` JSON, not raw, messy shell stdout.
2. **Structured Output**: The LLM must return its response in a strict Pydantic JSON schema (`SuggestedFix`), never as raw conversational text.
3. **No Direct Execution**: The AI cannot execute commands on the user's machine. It can only propose a `SuggestedFix`, which the backend translates into a Jinja2 template and validates before presenting it to the user for manual execution.

---

## 4. Safety Boundaries

If an AI provider fails, hallucinated a dangerous command, or acts maliciously, our architecture guarantees safety through isolation:

*   **Boundary 1**: AI output is forced into JSON schema. Non-conforming output is rejected.
*   **Boundary 2**: AI proposals are mapped to predefined Jinja2 templates.
*   **Boundary 3**: All rendered templates are scanned by `SafetyFilter.validate()` before being sent to the user.
