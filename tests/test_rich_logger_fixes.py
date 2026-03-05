#!/usr/bin/env python
"""
Unit tests for RichLogger UI fixes (v1.1.1).

Tests cover:
  - Debounce interval increased from 50ms to 200ms
  - Streaming preview throttle increased from 120 to 300 chars
  - Tree guide_style set to empty string (no line artifacts)
  - Rule separators removed from forensic report output
  - No repeated horizontal lines in terminal output
"""

import pytest
import time
from unittest.mock import MagicMock, patch, Mock
from io import StringIO
from typing import Any, cast


# ─────────────────────────────────────────────────────────────────
# 1. Test Debounce Interval Configuration
# ─────────────────────────────────────────────────────────────────
class TestDebounceInterval:
    """Verify debounce interval is set to 200ms (was 50ms)."""
    
    def test_min_update_interval_is_200ms(self):
        """Debounce interval should be 200ms to reduce Live widget refreshes."""
        from jasper.cli.main import RichLogger
        
        # Create mock board context
        board_context = {
            "live": MagicMock(),
            "board_panel": MagicMock(),
            "planning_node": MagicMock(),
            "execution_node": MagicMock(),
            "synthesis_node": MagicMock(),
        }
        
        logger = RichLogger(board_context)
        
        # Verify debounce is 200ms
        assert logger._min_update_interval == 0.2, \
            f"Expected _min_update_interval=0.2 (200ms), got {logger._min_update_interval}"
        print("   ✅ Debounce interval: 200ms")
    
    def test_debounce_logic_respects_interval(self):
        """Verify _should_update_live() enforces the debounce interval."""
        from jasper.cli.main import RichLogger
        
        board_context = {
            "live": MagicMock(),
            "board_panel": MagicMock(),
            "planning_node": MagicMock(),
            "execution_node": MagicMock(),
            "synthesis_node": MagicMock(),
        }
        
        logger = RichLogger(board_context)
        
        # First call should return True (no prior update)
        assert logger._should_update_live() is True, "First call should allow update"
        
        # Immediate second call should return False (within 200ms)
        assert logger._should_update_live() is False, "Second call should be debounced"
        
        # After 200ms, should allow update
        time.sleep(0.21)
        assert logger._should_update_live() is True, "Call after 200ms should be allowed"
        
        print("   ✅ Debounce logic works correctly")


# ─────────────────────────────────────────────────────────────────
# 2. Test Streaming Preview Throttle
# ─────────────────────────────────────────────────────────────────
class TestStreamingPreviewThrottle:
    """Verify synthesis preview throttle is 300 chars (was 120)."""
    
    def test_preview_update_threshold_is_300(self):
        """Preview should only update every 300 accumulated characters."""
        from jasper.cli.main import RichLogger
        
        board_context = {
            "live": MagicMock(),
            "board_panel": MagicMock(),
            "planning_node": MagicMock(),
            "execution_node": MagicMock(),
            "synthesis_node": MagicMock(),
        }
        
        logger = RichLogger(board_context)
        
        assert logger._preview_update_every_chars == 300, \
            f"Expected _preview_update_every_chars=300, got {logger._preview_update_every_chars}"
        print("   ✅ Synthesis preview throttle: 300 chars")
    
    def test_synthesis_buffer_accumulation(self):
        """Verify synthesis buffer only triggers updates at 300+ char threshold."""
        from jasper.cli.main import RichLogger
        
        board_context = {
            "live": MagicMock(),
            "board_panel": MagicMock(),
            "planning_node": MagicMock(),
            "execution_node": MagicMock(),
            "synthesis_node": MagicMock(),
        }
        
        logger = RichLogger(board_context)
        
        # Simulate streaming small chunks
        logger.synthesis_buffer = "A" * 250  # Below threshold
        char_delta = len(logger.synthesis_buffer) - logger._last_stream_update_chars
        
        should_update = char_delta >= logger._preview_update_every_chars
        assert not should_update, "Should NOT update at 250 chars (threshold is 300)"
        
        # Continue to 320 chars
        logger.synthesis_buffer = "A" * 320  # Above threshold
        char_delta = len(logger.synthesis_buffer) - logger._last_stream_update_chars
        
        should_update = char_delta >= logger._preview_update_every_chars
        assert should_update, "Should update at 320 chars (exceeds 300 threshold)"
        
        print("   ✅ Synthesis buffer accumulation respects 300-char threshold")


# ─────────────────────────────────────────────────────────────────
# 3. Test Tree Guide Style Configuration
# ─────────────────────────────────────────────────────────────────
class TestTreeGuideStyle:
    """Verify tree guide_style is empty string (eliminates line artifacts)."""
    
    def test_build_persistent_board_has_empty_guide_style(self):
        """Tree should have empty guide_style to prevent horizontal line artifacts."""
        from jasper.cli.interface import build_persistent_board
        
        board_panel, planning_node, execution_node, synthesis_node = build_persistent_board()
        
        # The root_tree is inside board_panel.renderable
        root_tree = cast(Any, board_panel.renderable)
        
        # Verify guide_style is empty string
        assert root_tree.guide_style == "", (
            f"Expected guide_style='', got guide_style={root_tree.guide_style!r}"
        )
        
        print("   ✅ Tree guide_style is empty (no connecting lines)")


# ─────────────────────────────────────────────────────────────────
# 4. Test Rule Separators Removed
# ─────────────────────────────────────────────────────────────────
class TestRuleSeparatorsRemoved:
    """Verify Rule separators are removed from forensic report output."""
    
    def test_render_forensic_report_no_rule_separators(self):
        """Forensic report Group should not contain Rule objects."""
        from jasper.cli.interface import render_forensic_report
        from jasper.core.state import FinalReport, ReportMode, ConfidenceBreakdown
        from rich.rule import Rule
        
        # Create minimal test report
        report = FinalReport(
            query="Test query",
            report_mode=ReportMode.BUSINESS_MODEL,
            synthesis_text="Test synthesis content",
            is_valid=True,
            confidence_score=0.75,
            confidence_breakdown=ConfidenceBreakdown(
                data_coverage=0.8,
                data_quality=0.8,
                inference_strength=0.75,
                overall=0.78
            ),
            tickers=["TEST"],
            data_sources=["Test Source"],
            version="1.1.1",
            evidence_log=[],
            audit_trail=[]
        )
        
        result_group = render_forensic_report(report)
        
        # Check that no Rule objects exist in the Group
        has_rule = any(isinstance(item, Rule) for item in result_group.renderables)
        
        assert not has_rule, \
            "Forensic report should not contain Rule separators (visual noise)"
        
        print("   ✅ Rule separators removed from forensic report")
    
    def test_render_final_report_no_rule_separators(self):
        """Final report should not contain Rule separators in content group."""
        from jasper.cli.interface import render_final_report
        from rich.rule import Rule
        
        answer = "Test answer about Apple's business model"
        tickers = ["AAPL"]
        sources = ["yfinance", "Alpha Vantage"]
        
        report_panel = render_final_report(answer, tickers, sources)
        
        # The content_group is inside the panel
        content_group = report_panel.renderable  # type: ignore
        
        # Check that no Rule objects exist in the Group
        has_rule = any(isinstance(item, Rule) for item in content_group.renderables)  # type: ignore
        
        assert not has_rule, \
            "Final report content should not contain Rule separators"
        
        print("   ✅ Rule separators removed from final report")


# ─────────────────────────────────────────────────────────────────
# 5. Integration Test: Complete Logger Lifecycle
# ─────────────────────────────────────────────────────────────────
class TestLoggerIntegration:
    """End-to-end test of RichLogger with all fixes applied."""
    
    def test_logger_event_flow_with_debounce(self):
        """Verify logger processes events with debounce applied."""
        from jasper.cli.main import RichLogger
        
        board_context = {
            "live": MagicMock(),
            "board_panel": MagicMock(),
            "planning_node": MagicMock(),
            "execution_node": MagicMock(),
            "synthesis_node": MagicMock(),
        }
        
        logger = RichLogger(board_context)
        
        # Simulate event sequence
        logger.log("PLANNER_STARTED", {})
        assert logger._should_update_live() is False, "Second update should be debounced"
        
        # Wait for debounce window
        time.sleep(0.21)
        assert logger._should_update_live() is True, "Update allowed after debounce"
        
        logger.log("PLAN_CREATED", {"plan": [{"description": "Task 1"}]})
        
        print("   ✅ Logger processes events with debounce")
    
    def test_configuration_matches_expected_values(self):
        """Verify all configuration changes are in place."""
        from jasper.cli.main import RichLogger
        from jasper.cli.interface import build_persistent_board
        
        # Test debounce interval
        board_context = {
            "live": MagicMock(),
            "board_panel": MagicMock(),
            "planning_node": MagicMock(),
            "execution_node": MagicMock(),
            "synthesis_node": MagicMock(),
        }
        logger = RichLogger(board_context)
        
        config_checks = {
            "_min_update_interval": (logger._min_update_interval, 0.2),
            "_preview_update_every_chars": (logger._preview_update_every_chars, 300),
        }
        
        for param_name, (actual, expected) in config_checks.items():
            assert actual == expected, \
                f"{param_name}: expected {expected}, got {actual}"
        
        # Test tree guide_style
        board_panel, _, _, _ = build_persistent_board()
        root_tree = cast(Any, board_panel.renderable)
        assert root_tree.guide_style == "", (
            f"guide_style: expected '', got {root_tree.guide_style!r}"
        )
        
        print("   ✅ All configuration parameters match expected values")


# ─────────────────────────────────────────────────────────────────
# 6. Test Output Clarity
# ─────────────────────────────────────────────────────────────────
class TestOutputClarity:
    """Verify output has no visual artifacts or repeated lines."""
    
    def test_no_repeated_horizontal_lines_in_config(self):
        """Verify configuration prevents line repetition artifacts."""
        from jasper.cli.main import RichLogger
        from jasper.cli.interface import build_persistent_board
        
        # Check debounce prevents excessive redraws
        board_context = {
            "live": MagicMock(),
            "board_panel": MagicMock(),
            "planning_node": MagicMock(),
            "execution_node": MagicMock(),
            "synthesis_node": MagicMock(),
        }
        logger = RichLogger(board_context)
        
        # At 0.2s debounce, Live widget (4 refreshes/sec) will group updates
        # preventing excessive re-rendering of tree guide lines
        assert logger._min_update_interval == 0.2, \
            "Debounce must be ≥200ms to prevent line artifacts"
        
        # Check tree guide lines are disabled
        board_panel, _, _, _ = build_persistent_board()
        root_tree = board_panel.renderable  # type: ignore
        assert root_tree.guide_style == "", (  # type: ignore
            "guide_style must be empty to prevent line rendering"
        )
        
        print("   ✅ Configuration prevents line repetition artifacts")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Running RichLogger UI Fixes Test Suite (v1.1.1)")
    print("="*70 + "\n")
    
    # Run all test classes
    test_classes = [
        TestDebounceInterval,
        TestStreamingPreviewThrottle,
        TestTreeGuideStyle,
        TestRuleSeparatorsRemoved,
        TestLoggerIntegration,
        TestOutputClarity,
    ]
    
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n[{test_class.__name__}]")
        print(f"  {test_class.__doc__.strip()}")
        print()
        
        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith("test_")]
        
        for method_name in test_methods:
            try:
                method = getattr(test_instance, method_name)
                method()
                passed += 1
            except AssertionError as e:
                print(f"   ❌ {method_name}: {e}")
                failed += 1
            except Exception as e:
                print(f"   ❌ {method_name}: Unexpected error: {e}")
                failed += 1
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    exit(0 if failed == 0 else 1)
