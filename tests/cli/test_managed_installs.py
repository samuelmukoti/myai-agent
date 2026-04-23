from types import SimpleNamespace
from unittest.mock import patch

from myai_cli.config import (
    format_managed_message,
    get_managed_system,
    recommended_update_command,
)
from myai_cli.main import cmd_update
from tools.skills_hub import OptionalSkillSource


def test_get_managed_system_homebrew(monkeypatch):
    monkeypatch.setenv("MYAI_AGENT_MANAGED", "homebrew")

    assert get_managed_system() == "Homebrew"
    assert recommended_update_command() == "brew upgrade myai-agent"


def test_format_managed_message_homebrew(monkeypatch):
    monkeypatch.setenv("MYAI_AGENT_MANAGED", "homebrew")

    message = format_managed_message("update MyAIOne Agent")

    assert "managed by Homebrew" in message
    assert "brew upgrade myai-agent" in message


def test_recommended_update_command_defaults_to_myai_update(monkeypatch):
    monkeypatch.delenv("MYAI_AGENT_MANAGED", raising=False)

    assert recommended_update_command() == "myai update"


def test_cmd_update_blocks_managed_homebrew(monkeypatch, capsys):
    monkeypatch.setenv("MYAI_AGENT_MANAGED", "homebrew")

    with patch("myai_cli.main.subprocess.run") as mock_run:
        cmd_update(SimpleNamespace())

    assert not mock_run.called
    captured = capsys.readouterr()
    assert "managed by Homebrew" in captured.err
    assert "brew upgrade myai-agent" in captured.err


def test_optional_skill_source_honors_env_override(monkeypatch, tmp_path):
    optional_dir = tmp_path / "optional-skills"
    optional_dir.mkdir()
    monkeypatch.setenv("MYAI_AGENT_OPTIONAL_SKILLS", str(optional_dir))

    source = OptionalSkillSource()

    assert source._optional_dir == optional_dir
