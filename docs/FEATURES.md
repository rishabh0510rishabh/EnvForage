# EnvForage Feature Matrix

The EnvForage platform is categorized into five distinct feature pillars, representing the complete capabilities introduced throughout the implementation plan.

## 1. Local System Introspection
- **Deterministic Hardware Extraction:** Analyzes OS Kernels, CPU instruction sets (x86/ARM), and active Python environments.
- **GPU Capability Profiling:** Executes and parses low-level sub-processes (`nvidia-smi`, `rocminfo`) to detect VRAM, CUDA levels, and ROCm compatibility.
- **Anonymous Hardware Fingerprinting:** Generates non-reversible SHA-256 hashes of system setups to track recurring hardware profiles without compromising PII.

## 2. Dynamic Compatibility Engine
- **Matrix Resolution:** Intersects local hardware telemetry against continuously updated JSON rulesets (Python, CUDA, PyTorch versions).
- **Negative-Lookahead Script Generation:** Compiles deterministic bash and PS1 scripts via Jinja2, gated by strict Regex guards that prevent command injection (`rm -rf`).
- **Cryptographic Signatures:** Secures generated installation scripts with SHA-256 checksums to verify tamper resistance prior to local execution.

## 3. AI Troubleshooting & Resilience
- **Isolated LLM Gateway:** Routes diagnostic context to multiple providers (Anthropic Claude 3.5, OpenAI, OpenRouter, or local Ollama instances).
- **Real-time SSE Streaming:** Streams Markdown AI resolution instructions back to the UI or CLI character-by-character for zero perceived latency.
- **Token Budgeting & PII Sanitization:** Scrubs MAC addresses and network IPs from logs before passing data to models, enforcing strict token-generation limits.

## 4. Telemetry & Observability
- **Prometheus & Structured Logging:** Exposes `/metrics` for latency histograms and connection pools; outputs all logs as `structlog` JSON for Datadog/ELK ingestion.
- **Database Query Profiling:** Logs and alerts on ORM queries exceeding 50ms execution thresholds.
- **Frontend Crash Tracking:** Integrates Sentry React Error Boundaries and PostHog anonymous usage metrics.

## 5. Enterprise Integrations
- **Webhook Architecture:** Asynchronous event dispatching system utilizing background tasks to POST HMAC-secured payloads on system events.
- **Plugin System Loader:** Allows organizations to dynamically inject custom JSON compatibility matrices without forking the core engine.
- **Kubernetes Ready:** Fully packaged Helm charts with automated HPA (Horizontal Pod Autoscaler), Ingress, and StatefulSet configurations for Redis/Postgres.
