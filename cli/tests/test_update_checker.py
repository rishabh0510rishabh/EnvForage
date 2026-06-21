from unittest.mock import patch, MagicMock
import pytest
import json
import httpx

from envforage.utils import check_for_updates


@patch("envforage.__version__", "0.0.0")
@patch("sys.argv", ["envforage"])
@patch("httpx.Client")
@patch("click.echo")
def test_update_available(mock_echo, mock_client_class) -> None:
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.9.9"}}
    mock_client.get.return_value = mock_response

    check_for_updates()

    mock_echo.assert_called_once()
    assert "[!] A new version of envforage is available: 99.9.9" in mock_echo.call_args[0][0]
    assert mock_echo.call_args[1]["err"] is True


@patch("sys.argv", ["envforage"])
@patch("httpx.Client")
@patch("click.echo")
def test_no_update_available(mock_echo, mock_client_class) -> None:
    from envforage import __version__

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": __version__}}
    mock_client.get.return_value = mock_response

    check_for_updates()

    mock_echo.assert_not_called()


@patch("sys.argv", ["envforage"])
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


@patch("sys.argv", ["envforage"])
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


@patch("sys.argv", ["envforage", "--quiet"])
@patch("httpx.Client")
@patch("click.echo")
def test_quiet_flag_suppresses_check(mock_echo, mock_client_class) -> None:
    check_for_updates()
    mock_client_class.assert_not_called()
    mock_echo.assert_not_called()


@patch("sys.argv", ["envforage", "-q"])
@patch("httpx.Client")
@patch("click.echo")
def test_q_flag_suppresses_check(mock_echo, mock_client_class) -> None:
    check_for_updates()
    mock_client_class.assert_not_called()
    mock_echo.assert_not_called()


@patch("envforage.__version__", "0.0.0")
@patch("sys.argv", ["envforage"])
@patch("httpx.Client")
@patch("click.echo")
@patch("envforage.config.load_config")
def test_update_available_notification_mode(mock_load_config, mock_echo, mock_client_class) -> None:
    mock_config = MagicMock()
    mock_config.auto_update = False
    mock_load_config.return_value = mock_config

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.9.9"}}
    mock_client.get.return_value = mock_response

    check_for_updates()

    mock_echo.assert_called_once()
    assert "[!] A new version of envforage is available: 99.9.9" in mock_echo.call_args[0][0]
    assert "Run 'envforage upgrade' to update" in mock_echo.call_args[0][0]


@patch("envforage.__version__", "0.0.0")
@patch("sys.argv", ["envforage"])
@patch("httpx.Client")
@patch("click.confirm")
@patch("envforage.config.load_config")
@patch("sys.stdin.isatty", return_value=True)
@patch("envforage.utils.run_upgrade")
def test_update_available_prompt_mode_yes(mock_run_upgrade, mock_isatty, mock_load_config, mock_confirm, mock_client_class) -> None:
    mock_config = MagicMock()
    mock_config.auto_update = True
    mock_load_config.return_value = mock_config

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.9.9"}}
    mock_client.get.return_value = mock_response

    mock_confirm.return_value = True

    with pytest.raises(SystemExit) as excinfo:
        check_for_updates()

    assert excinfo.value.code == 0
    mock_confirm.assert_called_once()
    mock_run_upgrade.assert_called_once_with(interactive=False)


@patch("sys.frozen", True, create=True)
@patch("httpx.Client")
@patch("subprocess.Popen")
@patch("builtins.open")
def test_run_upgrade_frozen_exe(mock_open, mock_popen, mock_client_class) -> None:
    from envforage.utils import run_upgrade
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tag_name": "v99.9.9",
        "assets": [
            {"name": "envforage-v99.9.9-setup.exe", "browser_download_url": "https://github.com/test/releases/download/envforage-v99.9.9-setup.exe"}
        ]
    }
    mock_client.get.return_value = mock_response

    mock_stream_response = MagicMock()
    mock_stream_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]
    mock_client.stream.return_value.__enter__.return_value = mock_stream_response

    with pytest.raises(SystemExit) as excinfo:
        run_upgrade(interactive=False)

    assert excinfo.value.code == 0
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert args[0].endswith("envforage-v99.9.9-setup.exe")
    assert "/SILENT" in args
    assert "/FORCECLOSEAPPLICATIONS" in args


@patch("sys.frozen", False, create=True)
@patch("subprocess.run")
def test_run_upgrade_pip_interactive(mock_run) -> None:
    from envforage.utils import run_upgrade
    mock_run.return_value.returncode = 0

    run_upgrade(interactive=True)
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "pip" in args
    assert "install" in args
    assert "--upgrade" in args
    assert "envforage" in args
