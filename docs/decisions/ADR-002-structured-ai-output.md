# ADR-002: Structured AI Output over Raw LLM Text

**Status**: Accepted  
**Date**: 2026-05-06  
**Author**: EnvForage Architecture

---

## Context

The AI troubleshooting layer needs to return remediation guidance. The options were:
1. Return raw LLM text (stream to frontend)
2. Enforce structured JSON output (Pydantic models)

## Decision

Always use structured JSON output with Pydantic validation. AI never produces
raw shell commands — it suggests `repair_template_id` values, and the Template
Engine renders the actual scripts.

## Rationale

1. **Safety**: Raw LLM text can contain dangerous commands. Structured output prevents this.
2. **Prompt injection prevention**: Structured schemas limit what AI can express.
3. **Auditability**: Structured responses are loggable, comparable, testable.
4. **Template Engine integration**: Repair scripts must go through our safety-validated
   template system, not be raw LLM output.

## Alternatives Considered

- **Raw text streaming**: Rejected — cannot guarantee safety; hard to audit; enables injection.
- **Hybrid (structured + optional raw text)**: Rejected — the optional raw text path creates
  a safety hole that could be exploited.

## Tradeoffs

- Structured output limits AI's expression (intentional — that's the safety mechanism).
- Requires more prompt engineering to get reliable structured responses.
- Structured output may not work well with all LLM providers (mitigated by MockProvider for testing).

## Scalability

This design scales to any LLM provider as long as they support JSON mode or function calling.
The `LLMProvider` abstraction handles provider-specific structured output APIs.
