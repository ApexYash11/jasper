from typer.testing import CliRunner
from jasper.cli.main import app
from jasper.core.controller import JasperController
from jasper.agent.planner import Planner
from jasper.agent.executor import Executor
from jasper.agent.validator import validator
from jasper.agent.synthesizer import Synthesizer
from jasper.core.state import Jasperstate

from jasper.cli.interface import render_mission_board

runner = CliRunner()

def test_mission_control_rendering():
    """Verify that mission control (Live Tree) renders without errors."""
    tasks = [
        {"description": "Task 1", "status": "success", "detail": ""},
        {"description": "Task 2", "status": "running", "detail": "Working..."},
        {"description": "Task 3", "status": "pending", "detail": ""},
    ]
    # Test with overall status (the new parameter)
    panel = render_mission_board(tasks, "[EXECUTING] Testing...")
    assert panel is not None
    
    # Test without tasks
    panel_empty = render_mission_board([], "[PLANNING] Starting...")
    assert panel_empty is not None

def test_imports():
    """Verify that all core components can be imported."""
    assert JasperController is not None
    assert Planner is not None
    assert Executor is not None
    assert validator is not None
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
    # Typer help output usually contains "Usage" and "Commands"
    assert "Usage" in result.stdout
    assert "Commands" in result.stdout

def test_cli_doctor_fail_no_env():
    """Verify the 'doctor' command runs (it might fail if env vars are missing, but it should finish)."""
    # We don't necessarily expect success if API keys are missing, 
    # but we expect it not to crash with a traceback.
    result = runner.invoke(app, ["doctor"])
    # It might exit with 1 if checks fail, and that's okay for a smoke test as long as no traceback.
    assert "Running Diagnostics..." in result.stdout
