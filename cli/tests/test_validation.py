from unittest.mock import patch

from envforge_agent.validation import (
    check_python_version,
    check_git_installed,
    check_docker_installed,
    validate_environment,
)


def test_python_version_check_passes() -> None:
    result = check_python_version((3, 10))
    assert result.is_valid
    assert result.errors == []


@patch("shutil.which")
def test_git_check_fails_when_git_missing(mock_which) -> None:
    mock_which.return_value = None

    result = check_git_installed()

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "Git" in result.errors[0]


@patch("shutil.which")
def test_git_check_passes_when_git_exists(mock_which) -> None:
    mock_which.return_value = "/usr/bin/git"

    result = check_git_installed()

    assert result.is_valid
    assert result.errors == []

@patch("shutil.which")
def test_docker_check_fails_when_docker_missing(mock_which) -> None:
    mock_which.return_value = None

    result = check_docker_installed()

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "Docker" in result.errors[0]


@patch("shutil.which")
def test_docker_check_passes_when_docker_exists(mock_which) -> None:
    mock_which.return_value = "/usr/bin/docker"

    result = check_docker_installed()

    assert result.is_valid
    assert result.errors == []


@patch("envforge_agent.validation.check_python_version")
@patch("envforge_agent.validation.check_git_installed")
@patch("envforge_agent.validation.check_docker_installed")
def test_validate_environment_aggregates_results(
    mock_docker,
    mock_git,
    mock_python,
) -> None:
    from envforge_agent.validation import ValidationResult

    py_result = ValidationResult()
    git_result = ValidationResult()
    docker_result = ValidationResult()

    git_result.errors.append("Git missing")
    docker_result.errors.append("Docker missing")

    mock_python.return_value = py_result
    mock_git.return_value = git_result
    mock_docker.return_value = docker_result

    result = validate_environment()

    assert len(result.errors) == 2
    assert "Git missing" in result.errors
    assert "Docker missing" in result.errors