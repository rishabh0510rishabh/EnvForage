"""Tests for Redis caching in the script generation service."""

import json
import uuid
from types import SimpleNamespace

from app.compatibility.models import ResolvedEnvironment, ResolvedPackage
from app.schemas.script import GenerationRequest
from app.services import script_service


class FakeDB:
    def __init__(self) -> None:
        self.added = []

    def add(self, item) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        return None


class FakeRedis:
    def __init__(self, cached: str | None = None) -> None:
        self.cached = cached
        self.get_calls = []
        self.set_calls = []

    async def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        return self.cached

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.set_calls.append((key, value, ex))
        self.cached = value


class FakeRenderer:
    def render_all(self, output_formats, ctx):
        package = ctx.resolved.packages[0]
        return [
            SimpleNamespace(
                filename="requirements.txt",
                content=f"{package.name}=={package.version}",
                size_bytes=len(package.name) + len(package.version) + 2,
            )
        ]


def _profile():
    return SimpleNamespace(
        id=uuid.uuid4(),
        slug="pytorch-cuda",
        name="PyTorch CUDA",
        os_support=["LINUX", "WSL"],
        cuda_required=False,
        packages=[
            SimpleNamespace(
                package_name="torch",
                version_spec="2.1.0",
                cuda_variant=None,
                install_order=0,
            )
        ],
    )


def _request() -> GenerationRequest:
    return GenerationRequest(
        profile_id="pytorch-cuda",
        target_os="LINUX",
        python_version="3.11",
        cuda_version=None,
        overrides={},
        output_formats=["requirements.txt"],
    )


def _resolved(version: str = "2.1.0") -> ResolvedEnvironment:
    return ResolvedEnvironment(
        python_version="3.11",
        cuda_version=None,
        target_os="LINUX",
        packages=[ResolvedPackage(name="torch", version=version)],
        warnings=[],
    )


async def _fake_redis_client(redis: FakeRedis) -> FakeRedis:
    return redis


async def test_generate_scripts_returns_cached_resolved_environment(monkeypatch):
    cached = _resolved(version="2.1.0")
    redis = FakeRedis(json.dumps(cached.to_dict()))

    class ResolverShouldNotRun:
        async def resolve(self, **kwargs):
            raise AssertionError("resolver should not run on cache hit")

    monkeypatch.setattr(
        script_service, "get_redis_client", lambda: _fake_redis_client(redis)
    )
    monkeypatch.setattr(script_service, "_resolver", ResolverShouldNotRun())
    monkeypatch.setattr(script_service, "_renderer", FakeRenderer())

    response = await script_service.generate_scripts(FakeDB(), _profile(), _request())

    assert response.resolved_packages[0].version == "2.1.0"
    assert response.scripts[0].content == "torch==2.1.0"
    assert len(redis.get_calls) == 1
    assert redis.set_calls == []


async def test_generate_scripts_caches_resolved_environment_on_miss(monkeypatch):
    redis = FakeRedis()

    class CountingResolver:
        def __init__(self) -> None:
            self.calls = 0

        async def resolve(self, **kwargs):
            self.calls += 1
            return _resolved(version="2.2.0")

    resolver = CountingResolver()
    monkeypatch.setattr(
        script_service, "get_redis_client", lambda: _fake_redis_client(redis)
    )
    monkeypatch.setattr(script_service, "_resolver", resolver)
    monkeypatch.setattr(script_service, "_renderer", FakeRenderer())

    response = await script_service.generate_scripts(FakeDB(), _profile(), _request())

    assert response.resolved_packages[0].version == "2.2.0"
    assert resolver.calls == 1
    assert len(redis.get_calls) == 1
    assert len(redis.set_calls) == 1
    cache_key, cache_value, cache_ttl = redis.set_calls[0]
    assert cache_key.startswith("compatibility_resolver:v1:")
    assert cache_ttl == 86400
    assert json.loads(cache_value)["packages"][0]["version"] == "2.2.0"
