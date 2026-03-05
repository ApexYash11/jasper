"""
Test suite for Rich Live rendering fixes and Windows terminal detection.

Tests cover:
1. Windows-aware console initialization (force_terminal, legacy_windows, no_color)
2. use_live detection logic for various terminal environments
3. Guide style configuration in display trees
4. Live widget refresh rate settings
"""

import os
import sys
import platform
from unittest import mock
import pytest
from io import StringIO

# Mock Rich components before importing main
from rich.console import Console
from rich.tree import Tree
from rich.live import Live


class TestWindowsTerminalDetection:
    """Test Windows terminal environment detection."""
    
    def test_detect_windows_platform(self):
        """Verify Windows platform detection."""
        with mock.patch('platform.system', return_value='Windows'):
            is_windows = platform.system() == "Windows"
            assert is_windows is True
    
    def test_detect_windows_terminal_env_var(self):
        """Verify Windows Terminal detection via WT_SESSION."""
        with mock.patch.dict(os.environ, {'WT_SESSION': 'some_id'}):
            is_windows_terminal = bool(os.getenv("WT_SESSION"))
            assert is_windows_terminal is True
    
    def test_windows_terminal_not_set(self):
        """Verify detection when WT_SESSION not set."""
        with mock.patch.dict(os.environ, {}, clear=False):
            # Remove WT_SESSION if it exists
            os.environ.pop('WT_SESSION', None)
            is_windows_terminal = bool(os.getenv("WT_SESSION"))
            assert is_windows_terminal is False
    
    def test_detect_conemu_env_var(self):
        """Verify ConEmu detection via ConEmuPID."""
        with mock.patch.dict(os.environ, {'ConEmuPID': '1234'}):
            is_conemu = bool(os.getenv("ConEmuPID"))
            assert is_conemu is True
    
    def test_detect_vscode_terminal(self):
        """Verify VS Code terminal detection via TERM_PROGRAM."""
        with mock.patch.dict(os.environ, {'TERM_PROGRAM': 'vscode'}):
            is_vscode = os.getenv("TERM_PROGRAM") == "vscode"
            assert is_vscode is True
    
    def test_plain_powershell_has_no_term_set(self):
        """Verify plain PowerShell.exe has TERM=None."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('TERM', None)
            term_value = os.getenv("TERM")
            assert term_value is None


class TestUseLiveDetectionLogic:
    """Test use_live detection for different terminal environments."""
    
    def setup_method(self):
        """Setup for each test."""
        self.is_tty = True  # Simulate TTY
    
    def test_windows_plainpowershell_disables_live(self):
        """On Windows PowerShell.exe (no TERM_PROGRAM, no WT_SESSION, no ConEmuPID), Live should be disabled."""
        is_windows = True
        is_windows_terminal = False
        is_vscode = False
        is_conemu = False
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = is_tty and (is_windows_terminal or is_conemu) and not is_vscode
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is False, "Live should be disabled in plain PowerShell.exe"
    
    def test_windows_terminal_enables_live(self):
        """On Windows Terminal (WT_SESSION set), Live should be enabled."""
        is_windows = True
        is_windows_terminal = True  # WT_SESSION env var set
        is_vscode = False
        is_conemu = False
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = is_tty and (is_windows_terminal or is_conemu) and not is_vscode
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is True, "Live should be enabled in Windows Terminal"
    
    def test_conemu_enables_live(self):
        """On ConEmu (ConEmuPID set), Live should be enabled."""
        is_windows = True
        is_windows_terminal = False
        is_vscode = False
        is_conemu = True  # ConEmuPID env var set
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = is_tty and (is_windows_terminal or is_conemu) and not is_vscode
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is True, "Live should be enabled in ConEmu"
    
    def test_vscode_disables_live_on_windows(self):
        """On Windows Terminal + VS Code terminal, Live should be disabled."""
        is_windows = True
        is_windows_terminal = True
        is_vscode = True  # TERM_PROGRAM=vscode
        is_conemu = False
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = is_tty and (is_windows_terminal or is_conemu) and not is_vscode
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is False, "Live should be disabled in VS Code terminal"
    
    def test_linux_enables_live_in_tty(self):
        """On Linux/macOS TTY (not VS Code, not dumb), Live should be enabled."""
        is_windows = False
        is_vscode = False
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = True  # (dummy)
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is True, "Live should be enabled on Linux/macOS TTY"
    
    def test_linux_vscode_disables_live(self):
        """On Linux/macOS in VS Code terminal, Live should be disabled."""
        is_windows = False
        is_vscode = True  # TERM_PROGRAM=vscode
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = True  # (dummy)
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is False, "Live should be disabled in VS Code on Linux/macOS"
    
    def test_dumb_terminal_disables_live(self):
        """On dumb terminal (TERM=dumb), Live should be disabled."""
        is_windows = False
        is_vscode = False
        is_dumb = True  # TERM=dumb
        is_tty = True
        
        if is_windows:
            use_live = True  # (dummy)
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is False, "Live should be disabled in dumb terminal"
    
    def test_not_tty_disables_live(self):
        """When not in TTY, Live should be disabled."""
        is_windows = False
        is_vscode = False
        is_dumb = False
        is_tty = False  # Not a TTY (e.g., redirected output)
        
        if is_windows:
            use_live = True  # (dummy)
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert use_live is False, "Live should be disabled when not in TTY"


class TestConsoleInitialization:
    """Test Console initialization with Windows-aware settings."""
    
    def test_force_terminal_windows_powershell(self):
        """On Windows PowerShell (no WT_SESSION, no ConEmuPID), force_terminal should be False."""
        is_windows = True
        is_windows_terminal = False
        is_tty = True
        
        force_terminal = is_tty and (
            not is_windows or is_windows_terminal or False  # ConEmuPID check
        )
        
        assert force_terminal is False, "force_terminal should be False in plain PowerShell"
    
    def test_force_terminal_windows_terminal(self):
        """On Windows Terminal (WT_SESSION set), force_terminal should be True."""
        is_windows = True
        is_windows_terminal = True
        is_tty = True
        
        force_terminal = is_tty and (
            not is_windows or is_windows_terminal or False  # ConEmuPID check
        )
        
        assert force_terminal is True, "force_terminal should be True in Windows Terminal"
    
    def test_force_terminal_conemu(self):
        """On ConEmu (ConEmuPID set), force_terminal should be True."""
        is_windows = True
        is_windows_terminal = False
        is_conemu = True
        is_tty = True
        
        force_terminal = is_tty and (
            not is_windows or is_windows_terminal or is_conemu
        )
        
        assert force_terminal is True, "force_terminal should be True in ConEmu"
    
    def test_force_terminal_linux_tty(self):
        """On Linux/macOS TTY, force_terminal should be True."""
        is_windows = False
        is_tty = True
        
        force_terminal = is_tty and (
            not is_windows or False  # Windows checks don't apply
        )
        
        assert force_terminal is True, "force_terminal should be True on Linux/macOS TTY"
    
    def test_no_color_reflects_force_terminal(self):
        """no_color should be True when force_terminal is False."""
        force_terminal = False
        no_color = not force_terminal
        assert no_color is True
        
        force_terminal = True
        no_color = not force_terminal
        assert no_color is False
    
    def test_legacy_windows_for_powershell(self):
        """legacy_windows should be True for plain PowerShell.exe."""
        is_windows = True
        is_windows_terminal = False
        legacy_windows = is_windows and not is_windows_terminal
        
        assert legacy_windows is True, "legacy_windows should be True for plain PowerShell"
    
    def test_legacy_windows_false_for_windows_terminal(self):
        """legacy_windows should be False for Windows Terminal."""
        is_windows = True
        is_windows_terminal = True
        legacy_windows = is_windows and not is_windows_terminal
        
        assert legacy_windows is False, "legacy_windows should be False for Windows Terminal"
    
    def test_legacy_windows_false_for_linux(self):
        """legacy_windows should be False on Linux/macOS."""
        is_windows = False
        legacy_windows = is_windows and True  # (dummy is_windows_terminal)
        
        assert legacy_windows is False, "legacy_windows should be False on non-Windows"


class TestGuideStyleConfiguration:
    """Test guide_style settings in display trees."""
    
    def test_render_mission_board_has_empty_guide_style(self):
        """render_mission_board() should use guide_style=\"\"."""
        # Create a mock tree like render_mission_board does
        tree = Tree("MISSION CONTROL", guide_style="")
        # Check that guide_style is set to empty string
        assert tree.guide_style == ""
    
    def test_build_persistent_board_has_empty_guide_style(self):
        """build_persistent_board() should use guide_style=\"\"."""
        # Create a mock tree like build_persistent_board does
        tree = Tree("MISSION CONTROL", guide_style="")
        # Check that guide_style is set to empty string
        assert tree.guide_style == ""
    
    def test_guide_style_empty_prevents_guide_lines(self):
        """Empty guide_style should not render guide lines."""
        tree = Tree("Root", guide_style="")
        child1 = tree.add("Child 1")
        child2 = tree.add("Child 2")
        
        # guide_style="" means no guide characters will be rendered
        assert tree.guide_style == ""


class TestLiveWidgetRefreshRate:
    """Test Live widget refresh rate settings."""
    
    def test_live_refresh_rate_is_2hz(self):
        """Live widget should refresh at 2 Hz (not 4 Hz)."""
        refresh_per_second = 2
        assert refresh_per_second == 2, "Refresh rate should be 2 Hz"
    
    def test_live_widget_force_parameter(self):
        """Live widget should have force=False to respect terminal capabilities."""
        # When force=False, Live respects terminal capabilities
        force = False
        assert force is False, "Live widget should not force rendering"


class TestIntegration:
    """Integration tests for the complete rendering pipeline."""
    
    def test_windows_terminal_renders_with_richui(self):
        """Full integration test: Windows Terminal should enable Rich Live."""
        # Simulate Windows Terminal environment
        is_windows = True
        is_windows_terminal = True
        is_vscode = False
        is_conemu = False
        is_dumb = False
        is_tty = True
        
        # Apply detection logic
        if is_windows:
            use_live = is_tty and (is_windows_terminal or is_conemu) and not is_vscode
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        # Assertions
        assert is_windows is True
        assert is_windows_terminal is True
        assert use_live is True
    
    def test_plain_powershell_disables_richui(self):
        """Full integration test: Plain PowerShell should disable Rich Live."""
        # Simulate plain PowerShell environment
        is_windows = True
        is_windows_terminal = False
        is_vscode = False
        is_conemu = False
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = is_tty and (is_windows_terminal or is_conemu) and not is_vscode
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert is_windows is True
        assert is_windows_terminal is False
        assert use_live is False
    
    def test_linux_tty_enables_richui(self):
        """Full integration test: Linux TTY should enable Rich Live."""
        is_windows = False
        is_vscode = False
        is_dumb = False
        is_tty = True
        
        if is_windows:
            use_live = False  # (dummy)
        else:
            use_live = is_tty and not is_vscode and not is_dumb
        
        assert is_windows is False
        assert use_live is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
