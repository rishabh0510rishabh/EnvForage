# ADR-001: REST over GraphQL

**Status**: Accepted  
**Date**: 2026-05-06  
**Author**: EnvForage Architecture

---

## Context

EnvForage needs an API style for frontend–backend communication.
The main candidates were REST and GraphQL.

## Decision

Use REST with OpenAPI documentation.

## Rationale

1. **Contributor accessibility**: REST is universally understood; GraphQL adds schema learning curve for new contributors.
2. **OpenAPI docs**: FastAPI auto-generates Swagger UI — excellent for contributor discovery.
3. **Simplicity**: Our query patterns are simple (list, get, post) — GraphQL's flexibility is overkill.
4. **Tooling**: REST tooling (curl, Postman, HTTPie) is ubiquitous; no special client needed.

## Alternatives Considered

- **GraphQL**: Rejected due to added complexity and overkill for the use case.
- **gRPC**: Rejected — browser client support is complex, contributor tooling is specialized.

## Tradeoffs

- REST requires careful endpoint versioning (mitigated with `/api/v1/` prefix).
- No automatic type sharing between frontend and backend (mitigated with OpenAPI codegen).

## Scalability

REST scales well for this use case. If we ever need real-time features, we'll add WebSockets or SSE as targeted additions, not replace REST.
