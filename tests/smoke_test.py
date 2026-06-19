from typer.testing import CliRunner
from jasper.cli.main import app
from jasper.core.controller import JasperController
from jasper.agent.planner import Planner
from jasper.agent.executor import Executor
from jasper.agent.validator import Validator
from jasper.agent.synthesizer import Synthesizer
from jasper.core.state import Jasperstate

from jasper.cli.interface import build_persistent_board

runner = CliRunner()


def test_mission_control_rendering():
    """Verify that mission control (Live Tree) renders without errors."""
    panel, planning_node, execution_node, synthesis_node = build_persistent_board()
    assert panel is not None
    assert planning_node is not None
    assert execution_node is not None
    assert synthesis_node is not None


def test_imports():
    """Verify that all core components can be imported."""
    assert JasperController is not None
    assert Planner is not None
    assert Executor is not None
    assert Validator is not None
    assert Synthesizer is not None
    assert Jasperstate is not None


def test_cli_version():
    """Verify the 'version' command works."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Jasper version" in result.stdout


def test_cli_help():
    """Verify the help command works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "Commands" in result.stdout


def test_cli_doctor_fail_no_env():
    """Verify the 'doctor' command runs (it might fail if env vars are missing, but it should finish)."""
    result = runner.invoke(app, ["doctor"])
    assert "Running Diagnostics..." in result.stdout
