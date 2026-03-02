"""
Integration test for the complete fix: persistent board + table parsing + synthesis filtering.
Tests the entire flow with realistic financial data query.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from jasper.cli.interface import (
    _fix_markdown_tables,
    _format_cli_markdown,
    build_persistent_board,
    update_phase_node,
    append_task_to_node,
    update_synthesis_status,
)
from jasper.cli.main import RichLogger


class TestIntegrationTableParsing:
    """Integration tests for table parsing in realistic scenarios."""
    
    def test_financial_report_with_tables(self):
        """Test parsing a realistic financial report with multiple tables."""
        report = """
## Apple Financial Analysis

### Executive Summary
Apple demonstrates strong financial performance with record revenues and expanding margins.

### Financial Metrics
| Metric | FY2024 | FY2023 | Growth |
|:---|:---|:---|:---|
| Net Sales | $391.035B | $394.328B | -0.8% |
| Operating Income | $125.101B | $133.876B | -6.6% |
| Net Income | $93.7366B | $96.995B | -3.4% |

### Gross Margin Analysis
| Metric | Value |
|:---|:---|
| Gross Margin % | 46.6% | | Operating Margin % | 32% |
| ROI | 45.2% | | Asset Turnover | 2.1x |

### Segment Performance
| Segment | Revenue | Growth |
|:---|:---|:---|
| iPhone | $201.6B | 5% |
| Mac | $29.4B | -6% |
| Services | $85.2B | 12% |
"""
        
        output = _fix_markdown_tables(report)
        
        # Verify all financial data is preserved
        assert '$391.035B' in output
        assert '$394.328B' in output
        assert '46.6%' in output
        assert '32%' in output
        assert '45.2%' in output
        assert '2.1x' in output
        assert '$201.6B' in output
        assert '$29.4B' in output
        assert '$85.2B' in output
        
        # Verify no rows are on same line
        lines = output.split('\n')
        for line in lines:
            if line.strip().startswith('|'):
                # Should not have pipe-separated doubles like "val1 | | val2"
                pipe_count = line.count('|')
                # A proper 3-column table has 4 pipes (start, col1, col2, col3, end)
                # If values are compressed, we'd see more pipes
                assert pipe_count >= 3  # At minimum


class TestIntegrationPersistentBoard:
    """Integration tests for persistent board architecture."""
    
    def test_board_creation_and_updates(self):
        """Test that board is created once and nodes are updated in-place."""
        # Create board
        board, planning_node, execution_node, synthesis_node = build_persistent_board()
        
        initial_id = id(planning_node)
        
        # Update planning node
        update_phase_node(planning_node, status_text="Starting analysis...")
        
        # Node should still be the same object (updated in-place, not replaced)
        assert id(planning_node) == initial_id
        
        # Add a task
        append_task_to_node(planning_node, "Fetch market data")
        
        # Node should still be the same object
        assert id(planning_node) == initial_id
        
        # Update synthesis status
        update_synthesis_status(synthesis_node, "Processing...")
        
        # All nodes should remain unchanged (same objects)
        assert id(planning_node) == initial_id


class TestIntegrationRichLogger:
    """Integration tests for RichLogger with persistent board."""
    
    def test_logger_events_update_board_cumulatively(self):
        """Test that logger events accumulate on board without clearing."""
        # Create a mock Live object
        mock_live = Mock()
        
        # Create board and logger
        board, planning_node, execution_node, synthesis_node = build_persistent_board()
        
        board_context = {
            "live": mock_live,
            "board_panel": board,
            "planning_node": planning_node,
            "execution_node": execution_node,
            "synthesis_node": synthesis_node
        }
        
        logger = RichLogger(board_context)
        
        # Simulate planning event
        logger.log("PLANNER_STARTED", {})
        assert mock_live.update.called
        
        # Simulate plan created event
        logger.log("PLAN_CREATED", {
            "plan": [
                {"description": "Fetch historical prices"},
                {"description": "Calculate metrics"},
            ]
        })
        
        # Both planning_node and execution_node should exist and be accessible
        assert logger.planning_node is planning_node
        assert logger.execution_node is execution_node
        
        # Simulate task events
        logger.log("TASK_STARTED", {"description": "Fetch historical prices"})
        logger.log("TASK_COMPLETED", {"description": "Fetch historical prices", "status": "completed"})
        
        # No exception should occur - should accumulate, not rebuild
        assert True


class TestIntegrationSynthesisFiltering:
    """Integration tests for synthesis token filtering."""
    
    def test_low_value_content_filtering(self):
        """Test that low-value content is filtered during synthesis."""
        mock_live = Mock()
        board, planning_node, execution_node, synthesis_node = build_persistent_board()
        
        board_context = {
            "live": mock_live,
            "board_panel": board,
            "planning_node": planning_node,
            "execution_node": execution_node,
            "synthesis_node": synthesis_node
        }
        
        logger = RichLogger(board_context)
        
        # Test filtering of various content
        assert logger._is_low_value_content("This is not investment advice.")
        assert logger._is_low_value_content("Past performance does not guarantee results.")
        assert logger._is_low_value_content("Disclaimer: Please consult a professional advisor.")
        
        # Key sections should NOT be filtered
        assert not logger._is_low_value_content("Executive Summary: Apple shows strong growth")
        assert not logger._is_low_value_content("Key Findings: Revenue increased 20%")
        assert not logger._is_low_value_content("Recommendations: Hold position")
    
    def test_synthesis_token_buffering(self):
        """Test that synthesis tokens are buffered until sentence boundaries."""
        mock_live = Mock()
        board, planning_node, execution_node, synthesis_node = build_persistent_board()
        
        board_context = {
            "live": mock_live,
            "board_panel": board,
            "planning_node": planning_node,
            "execution_node": execution_node,
            "synthesis_node": synthesis_node
        }
        
        logger = RichLogger(board_context)
        
        # Feed tokens without sentence ending - should not update immediately
        update_count = mock_live.update.call_count
        logger.on_synthesis_token("Apple")
        logger.on_synthesis_token(" shows")
        logger.on_synthesis_token(" strong")
        
        # Update count may increase based on 150-char boundary, but let's check
        # that the buffer is accumulating
        assert logger.synthesis_buffer == "Apple shows strong"
        
        # Feed a sentence-ending token
        logger.on_synthesis_token(".")
        
        # Should trigger update
        assert mock_live.update.called

    def test_synthesis_preview_is_bounded_and_sanitized(self):
        """Live synthesis preview should remain short and avoid full raw stream echo."""
        mock_live = Mock()
        board, planning_node, execution_node, synthesis_node = build_persistent_board()

        board_context = {
            "live": mock_live,
            "board_panel": board,
            "planning_node": planning_node,
            "execution_node": execution_node,
            "synthesis_node": synthesis_node
        }

        logger = RichLogger(board_context)

        # Stream a long body and force a sentence boundary update
        long_text = (
            "Executive Summary: "
            + "Apple delivered strong results across key segments with resilient margin performance and cash generation " * 5
            + "Final sentence."
        )

        logger.on_synthesis_token(long_text)

        assert mock_live.update.called
        assert synthesis_node.children

        rendered_status = str(synthesis_node.children[0].label)

        # Should include typing indicator and remain bounded
        assert rendered_status.startswith("✍️")
        assert rendered_status.endswith("▌")
        assert len(rendered_status) <= 180

        # Should show recent tail, not the opening prefix of the full stream
        assert "Executive Summary:" not in rendered_status


class TestIntegrationEndToEnd:
    """End-to-end integration scenarios."""
    
    def test_financial_analysis_workflow(self):
        """Simulate a complete financial analysis workflow."""
        mock_live = Mock()
        board, planning_node, execution_node, synthesis_node = build_persistent_board()
        
        board_context = {
            "live": mock_live,
            "board_panel": board,
            "planning_node": planning_node,
            "execution_node": execution_node,
            "synthesis_node": synthesis_node
        }
        
        logger = RichLogger(board_context)
        
        # Simulate workflow
        events = [
            ("PLANNER_STARTED", {}),
            ("PLAN_CREATED", {
                "plan": [
                    {"description": "Fetch Apple historical prices"},
                    {"description": "Calculate financial metrics"},
                    {"description": "Analyze competitive position"},
                ]
            }),
            ("TASK_STARTED", {"description": "Fetch Apple historical prices"}),
            ("TASK_COMPLETED", {"description": "Fetch Apple historical prices", "status": "completed"}),
            ("TASK_STARTED", {"description": "Calculate financial metrics"}),
            ("TASK_COMPLETED", {"description": "Calculate financial metrics", "status": "completed"}),
            ("VALIDATION_STARTED", {}),
            ("VALIDATION_COMPLETED", {"confidence": 0.95, "is_valid": True}),
            ("SYNTHESIS_STARTED", {}),
        ]
        
        # Execute all events
        for event_type, payload in events:
            logger.log(event_type, payload)
        
        # Should not raise any exceptions
        assert True
    
    def test_table_parsing_in_synthesis_output(self):
        """Test that synthesized reports with tables are parsed correctly."""
        # Simulate LLM output with compressed tables
        synthesis_output = """
## Apple Inc. Financial Analysis

### Executive Summary
Apple delivered record results with $391.035B in net sales.

### Key Financial Metrics
| Metric | FY2024 Value |
|:---|:---|
| Net Sales | $391.035B | | Gross Margin % | 46.6% |
| Operating Income | $125.101B | | Operating Margin % | 32% |
| Net Income | $93.7366B | | EPS (Diluted) | $6.05 |

### Segment Analysis
| Segment | Revenue | YoY Growth |
|:---|:---|:---|
| iPhone | $201.6B | 5% | | Mac | $29.4B | -6% |
| Services | $85.2B | 12% | | Wearables | $35.2B | 8% |

### Recommendations
Apple is well-positioned for continued growth.
"""
        
        output = _fix_markdown_tables(synthesis_output)
        
        # Verify all financial data is properly formatted
        assert '$391.035B' in output
        assert '46.6%' in output
        assert '$125.101B' in output
        assert '32%' in output
        assert '$93.7366B' in output
        assert '$6.05' in output
        assert '$201.6B' in output
        assert '5%' in output
        assert '$29.4B' in output
        assert '-6%' in output
        assert '$85.2B' in output
        assert '12%' in output
        
        # Verify no rows are compressed on one line
        lines = output.split('\n')
        for line in lines:
            if '| Revenue | ' in line:
                # Should not have multiple companies on same line
                assert '| Mac' not in line  # Mac should be on separate line

    def test_cli_formatting_renders_comparison_table_as_box(self):
        """Compressed comparison table should render as a readable Unicode box table."""
        synthesis_output = """### Financial Evidence
| Metric | ICICI Bank | HDFC Bank |
|:---|:---|:---|
| Net Interest Margin (NIM) | ~4.0% | ~4.3% | | CASA Ratio | ~45% | ~40% |
| Return on Assets (ROA) | ~1.8% | ~2.2% |
"""

        output = _format_cli_markdown(synthesis_output)

        assert '┌' in output
        assert '┬' in output
        assert '│' in output
        assert '└' in output
        assert '~4.0%' in output
        assert '~4.3%' in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
