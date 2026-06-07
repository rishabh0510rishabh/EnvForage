from unittest.mock import patch, MagicMock
import pytest
import json
import httpx

from envforge_agent.utils import check_for_updates


@patch("envforge_agent.__version__", "0.0.0")
@patch("sys.argv", ["envforge"])
@patch("httpx.Client")
@patch("click.echo")
def test_update_available(mock_echo, mock_client_class) -> None:
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {
            "version": "99.9.9"
        }
    }
    mock_client.get.return_value = mock_response

    check_for_updates()

    mock_echo.assert_called_once()
    assert "[!] A new version of envforge-agent is available: 99.9.9" in mock_echo.call_args[0][0]
    assert mock_echo.call_args[1]["err"] is True


@patch("sys.argv", ["envforge"])
@patch("httpx.Client")
@patch("click.echo")
def test_no_update_available(mock_echo, mock_client_class) -> None:
    from envforge_agent import __version__
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {
            "version": __version__
        }
    }
    mock_client.get.return_value = mock_response

    check_for_updates()

    mock_echo.assert_not_called()


@patch("sys.argv", ["envforge"])
@patch("httpx.Client")
@patch("click.echo")
def test_non_json_response_fails_silently(mock_echo, mock_client_class) -> None:
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "<html>", 0)
    mock_client.get.return_value = mock_response

    try:
        check_for_updates()
    except Exception as exc:
        pytest.fail(f"check_for_updates raised an exception on non-JSON response: {exc}")

    mock_echo.assert_not_called()


@patch("sys.argv", ["envforge"])
@patch("httpx.Client")
@patch("click.echo")
def test_network_error_fails_silently(mock_echo, mock_client_class) -> None:
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = httpx.ConnectError("Connection timed out")

    try:
        check_for_updates()
    except Exception as exc:
        pytest.fail(f"check_for_updates raised an exception on network error: {exc}")

    mock_echo.assert_not_called()


@patch("sys.argv", ["envforge", "--quiet"])
@patch("httpx.Client")
@patch("click.echo")
def test_quiet_flag_suppresses_check(mock_echo, mock_client_class) -> None:
    check_for_updates()
    mock_client_class.assert_not_called()
    mock_echo.assert_not_called()


@patch("sys.argv", ["envforge", "-q"])
@patch("httpx.Client")
@patch("click.echo")
def test_q_flag_suppresses_check(mock_echo, mock_client_class) -> None:
    check_for_updates()
    mock_client_class.assert_not_called()
    mock_echo.assert_not_called()
