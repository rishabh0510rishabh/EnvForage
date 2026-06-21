# ADR-009: OpenRouter as Primary LLM Gateway

## Status
Accepted

## Context
EnvForage's AI Troubleshooting Layer requires access to LLM models for structured
diagnosis and repair suggestion generation. The design doc (`AI_LAYER.md`)
originally planned three provider implementations:

1. **OpenAI** — direct GPT-4o / GPT-4-turbo API
2. **OpenRouter** — multi-model gateway (100+ models via one API)
3. **Ollama** — local inference (Llama 3, Mistral)

Implementing and maintaining three separate provider clients (each with unique
auth, rate limiting, error handling, and response formats) creates significant
maintenance overhead for a small team.

## Decision
We implement **OpenRouter as the sole production provider** for Phase 4.

OpenRouter acts as a universal gateway — it supports all major model families
(OpenAI, Anthropic, Google, Meta, Mistral) through a single unified API that is
compatible with the OpenAI chat completions format. This means:

- `OPENROUTER_MODEL=openai/gpt-4o` → routes to GPT-4o
- `OPENROUTER_MODEL=google/gemini-flash-2.0` → routes to Gemini Flash
- `OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct:free` → free Llama 3

The `MockProvider` remains available for testing and development.

## Implementation Details

- **Provider**: `app/ai/providers/openrouter.py`
- **Factory**: `app/ai/providers/__init__.py` → `get_provider()`
- **Config**: `ENVFORAGE_LLM_PROVIDER=openrouter` + `OPENROUTER_API_KEY` + `OPENROUTER_MODEL`
- **Features**: JSON mode, retry with exponential backoff, Pydantic parsing, token tracking

## Consequences

**Positive:**
- Single provider to maintain — reduces code surface and testing burden.
- Access to any model (GPT-4o, Claude, Gemini, Llama) via config change only.
- Free models available for development (`meta-llama/llama-3-8b-instruct:free`).
- API format is OpenAI-compatible, making future direct OpenAI migration trivial.

**Negative:**
- Dependency on OpenRouter's uptime (mitigated by retry logic).
- Small latency overhead vs direct API calls (~50-100ms per request).
- Free-tier models have limited context windows and capabilities.

**Mitigations:**
- `MockProvider` ensures tests never depend on network.
- Provider factory allows adding `OpenAIProvider` or `OllamaProvider` later with zero API changes.
- Retry logic with exponential backoff handles transient failures.

## Alternatives Considered

1. **Direct OpenAI only**: Locks us to one model family. No free-tier for dev.
2. **All three providers**: Too much maintenance for Phase 4 scope.
3. **LiteLLM**: Third-party library that wraps 100+ providers, but adds a heavy
   dependency and abstracts away control over retry/safety logic.
