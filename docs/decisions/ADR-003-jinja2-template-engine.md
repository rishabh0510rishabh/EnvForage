# ADR-003: Jinja2 for Template Engine

**Status**: Accepted  
**Date**: 2026-05-06  
**Author**: EnvForage Architecture

---

## Context

Script generation requires a template engine to render setup scripts, Dockerfiles,
and requirements files from validated environment data.

## Decision

Use Jinja2 as the template engine.

## Rationale

1. **Battle-tested**: Used in Ansible, Cookiecutter, Flask — extremely mature.
2. **Contributor-friendly**: Templates are plain-text files with intuitive `{{ var }}` syntax.
3. **Python-native**: First-class Python library; no FFI or external process needed.
4. **Safety controls**: Jinja2's sandboxed environment can restrict dangerous operations.
5. **Readable output**: Templates produce readable scripts, not generated garbage.

## Alternatives Considered

- **Python f-strings / string.Template**: Rejected — no loops, conditionals, or template
  inheritance; too limited for multi-section scripts.
- **Mako**: Rejected — allows arbitrary Python execution in templates (safety concern).
- **Handlebars (via subprocess)**: Rejected — unnecessary cross-language complexity.

## Tradeoffs

- Jinja2 templates can be tricky to debug for contributors unfamiliar with it.
  Mitigated by: good snapshot tests, clear template variable documentation, and
  example renders in test fixtures.

## Scalability

Jinja2 is synchronous but fast for our use case. If template rendering becomes
a bottleneck (unlikely), templates can be pre-compiled and cached.
