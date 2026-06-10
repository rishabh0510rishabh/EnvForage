"""Unit tests for the ML Framework Recommendation Engine."""

import pytest

from app.recommendation.engine import recommend_profiles
from app.schemas.diagnostic import DiagnosticReportSchema


def _make_report(
    *, gpus=None, ram_gb=16.0, os_name="Ubuntu 22.04", cpu_brand="Intel i7"
):
    return DiagnosticReportSchema(
        os={"name": os_name, "version": "22.04", "architecture": "x86_64"},
        cpu={"brand": cpu_brand, "cores": 8, "threads": 16},
        ram={"total_gb": ram_gb, "available_gb": ram_gb * 0.6},
        gpus=gpus or [],
    )


class TestNoGPU:
    def test_recommends_cpu_only(self):
        result = recommend_profiles(_make_report(gpus=[]))
        names = [p["name"] for p in result["recommended_profiles"]]
        assert "cpu-only" in names

    def test_recommends_sklearn(self):
        result = recommend_profiles(_make_report(gpus=[]))
        names = [p["name"] for p in result["recommended_profiles"]]
        assert "sklearn" in names


class TestLowVRAM:
    def test_under_4gb_recommends_nano(self):
        gpus = [{"name": "GTX 1050", "vram_gb": 2.0, "index": 0}]
        result = recommend_profiles(_make_report(gpus=gpus))
        assert result["recommended_profiles"][0]["name"] == "yolov8-nano"

    def test_under_4gb_warns(self):
        gpus = [{"name": "GTX 1050", "vram_gb": 3.5, "index": 0}]
        result = recommend_profiles(_make_report(gpus=gpus))
        assert any("VRAM" in w for w in result["warnings"])


class TestMediumVRAM:
    def test_4_to_8gb_recommends_pytorch_cuda(self):
        gpus = [{"name": "RTX 3060", "vram_gb": 6.0, "index": 0}]
        result = recommend_profiles(_make_report(gpus=gpus))
        assert result["recommended_profiles"][0]["name"] == "pytorch-cuda"

    def test_8gb_recommends_yolov8(self):
        gpus = [{"name": "RTX 4060", "vram_gb": 8.0, "index": 0}]
        result = recommend_profiles(_make_report(gpus=gpus))
        names = [p["name"] for p in result["recommended_profiles"]]
        assert "yolov8" in names


class TestHighVRAM:
    def test_over_8gb_recommends_tf_gpu(self):
        gpus = [{"name": "RTX 4090", "vram_gb": 24.0, "index": 0}]
        result = recommend_profiles(_make_report(gpus=gpus))
        assert result["recommended_profiles"][0]["name"] == "tf-gpu"

    def test_over_8gb_includes_pytorch_cuda(self):
        gpus = [{"name": "RTX 4090", "vram_gb": 24.0, "index": 0}]
        result = recommend_profiles(_make_report(gpus=gpus))
        names = [p["name"] for p in result["recommended_profiles"]]
        assert "pytorch-cuda" in names


class TestAppleSilicon:
    def test_detects_m1(self):
        result = recommend_profiles(
            _make_report(os_name="macOS Sonoma", cpu_brand="Apple M1")
        )
        assert result["recommended_profiles"][0]["name"] == "pytorch-mps"

    def test_detects_m3_pro(self):
        result = recommend_profiles(
            _make_report(os_name="macOS Ventura", cpu_brand="Apple M3 Pro")
        )
        assert result["recommended_profiles"][0]["name"] == "pytorch-mps"


class TestLowRAM:
    def test_low_ram_warning(self):
        result = recommend_profiles(_make_report(ram_gb=4.0))
        assert any("RAM" in w for w in result["warnings"])

    def test_normal_ram_no_warning(self):
        result = recommend_profiles(_make_report(ram_gb=16.0))
        ram_warnings = [w for w in result["warnings"] if "RAM" in w]
        assert len(ram_warnings) == 0


class TestRankOrdering:
    def test_profiles_are_ranked(self):
        gpus = [{"name": "RTX 4090", "vram_gb": 24.0, "index": 0}]
        result = recommend_profiles(_make_report(gpus=gpus))
        ranks = [p["rank"] for p in result["recommended_profiles"]]
        assert ranks == sorted(ranks)


class TestNegativeValues:
    def test_negative_ram_raises(self):
        with pytest.raises(ValueError, match="RAM"):
            recommend_profiles(_make_report(ram_gb=-16.0))

    def test_zero_ram_raises(self):
        with pytest.raises(ValueError, match="RAM"):
            recommend_profiles(_make_report(ram_gb=0.0))

    def test_negative_vram_raises(self):
        with pytest.raises(ValueError, match="VRAM"):
            gpus = [{"name": "RTX 4090", "vram_gb": -8.0, "index": 0}]
            recommend_profiles(_make_report(gpus=gpus))

    def test_zero_vram_raises(self):
        with pytest.raises(ValueError, match="VRAM"):
            gpus = [{"name": "RTX 4090", "vram_gb": 0.0, "index": 0}]
            recommend_profiles(_make_report(gpus=gpus))
