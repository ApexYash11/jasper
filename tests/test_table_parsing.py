"""
Unit tests for markdown table parsing with financial data support.
Tests the _fix_markdown_tables() function against various corrupted table formats.
"""

import pytest
from jasper.cli.interface import _fix_markdown_tables, _format_cli_markdown


class TestTableParsingBasic:
    """Basic table parsing tests."""
    
    def test_clean_table_unchanged(self):
        """A properly formatted table should pass through unchanged."""
        input_text = """| Metric | Value |
|:---|:---|
| Revenue | $130.5B |
| Net Income | $29.9B |"""
        
        output = _fix_markdown_tables(input_text)
        
        # Should have 4 lines (header, separator, 2 data rows)
        lines = [l for l in output.split('\n') if l.strip().startswith('|')]
        assert len(lines) == 4
        assert '| Metric | Value |' in output
        assert '| Revenue | $130.5B |' in output
    
    def test_single_row_table(self):
        """Single row table with one metric."""
        input_text = """| Metric | Value |
|:---|:---|
| Revenue | $200.0B |"""
        
        output = _fix_markdown_tables(input_text)
        assert '| Revenue | $200.0B |' in output
    
    def test_three_column_table(self):
        """Table with three columns."""
        input_text = """| Metric | 2023 | 2024 |
|:---|:---|:---|
| Revenue | $100B | $120B |
| Growth | 15% | 20% |"""
        
        output = _fix_markdown_tables(input_text)
        lines = [l for l in output.split('\n') if l.strip().startswith('|')]
        assert len(lines) == 4


class TestTableParsingCompressed:
    """Tests for compressed/malformed tables."""
    
    def test_two_rows_on_one_line(self):
        """Two data rows crammed into one table row."""
        input_text = """| Metric | Value |
|:---|:---|
| Revenue | $130.5B | | Net Income | $29.9B |"""
        
        output = _fix_markdown_tables(input_text)
        lines = [l for l in output.split('\n') if l.strip().startswith('|')]
        
        # Should split into two rows (header, separator, 2 data rows)
        assert len(lines) == 4
        assert '| Revenue | $130.5B |' in output
        assert '| Net Income | $29.9B |' in output
    
    def test_three_rows_compressed(self):
        """Three data rows crammed together."""
        input_text = """| Metric | Value |
|:---|:---|
| Rev | $1B | | Inc | $2B | | Margin | 30% |"""
        
        output = _fix_markdown_tables(input_text)
        lines = [l for l in output.split('\n') if l.strip().startswith('|')]
        
        # Should split into 3 rows + header + separator
        assert len(lines) >= 5
        assert '| Rev | $1B |' in output
        assert '| Inc | $2B |' in output
        assert '| Margin | 30% |' in output


class TestTableParsingFinancial:
    """Tests for financial data preservation."""
    
    def test_currency_formatting(self):
        """Preserve currency symbols and formatting."""
        input_text = """| Item | Amount |
|:---|:---|
| Revenue | $130.5B |
| Expenses | $50.2M |
| Income | $29,900.50 |"""
        
        output = _fix_markdown_tables(input_text)
        
        assert '$130.5B' in output
        assert '$50.2M' in output
        assert '$29,900.50' in output
    
    def test_percentage_formatting(self):
        """Preserve percentage values."""
        input_text = """| Metric | Percentage |
|:---|:---|
| Growth | 45.2% |
| Margin | 22.5% |
| ROI | 15% |"""
        
        output = _fix_markdown_tables(input_text)
        
        assert '45.2%' in output
        assert '22.5%' in output
        assert '15%' in output
    
    def test_scale_suffix_preservation(self):
        """Preserve B/M/K scale suffixes."""
        input_text = """| Metric | Value |
|:---|:---|
| Large | $1.2B |
| Medium | $500M |
| Small | $50K |"""
        
        output = _fix_markdown_tables(input_text)
        
        assert '$1.2B' in output
        assert '$500M' in output
        assert '$50K' in output
    
    def test_mixed_financial_data(self):
        """Table with mixed currency, percentages, and numbers."""
        input_text = """| Company | Revenue | Growth | Price |
|:---|:---|:---|:---|
| Apple | $383.3B | 28.3% | 192.53 |
| Google | $307.4B | 13% | 145.87 |"""
        
        output = _fix_markdown_tables(input_text)
        
        assert '$383.3B' in output
        assert '28.3%' in output
        assert '192.53' in output


class TestTableParsingEdgeCases:
    """Edge cases and error handling."""
    
    def test_empty_cells(self):
        """Handle tables with empty cells."""
        input_text = """| Metric | Value |
|:---|:---|
| Revenue | $100B |
| | |
| Net Income | $20B |"""
        
        output = _fix_markdown_tables(input_text)
        lines = [l for l in output.split('\n') if l.strip().startswith('|')]
        
        # Should preserve structure
        assert len(lines) >= 4
    
    def test_special_characters_in_cells(self):
        """Handle special characters within cells."""
        input_text = """| Company | Description |
|:---|:---|
| Apple Inc. | Consumer Electronics & Services |"""
        
        output = _fix_markdown_tables(input_text)
        assert 'Consumer Electronics & Services' in output
    
    def test_non_table_text(self):
        """Non-table text should pass through unchanged."""
        input_text = """This is some text.

| Item | Value |
|:---|:---|
| Test | $100 |

More text here."""
        
        output = _fix_markdown_tables(input_text)
        
        assert 'This is some text.' in output
        assert 'More text here.' in output
        assert '| Test | $100 |' in output
    
    def test_multiple_tables(self):
        """Multiple separate tables in one document."""
        input_text = """| Table1 | Value |
|:---|:---|
| Row1 | $100 |

| Table2 | Value |
|:---|:---|
| Row1 | $200 |"""
        
        output = _fix_markdown_tables(input_text)
        
        assert '| Row1 | $100 |' in output
        assert '| Row1 | $200 |' in output


class TestTableParsingMalformed:
    """Tests for more severely malformed tables."""
    
    def test_separator_row_compression(self):
        """Separator row itself might be compressed."""
        input_text = """| A | B |
|:---|:---|:---|:---|
| 1 | 2 |"""
        
        output = _fix_markdown_tables(input_text)
        
        # Should normalize separator to match column count
        lines = [l for l in output.split('\n') if l.strip().startswith('|')]
        assert len(lines) >= 3
    
    def test_column_count_inference(self):
        """Column count should be inferred from header or first row."""
        input_text = """| A | B | C |
|:---|:---|:---|
| 1 | 2 | 3 | | 4 | 5 | 6 |"""
        
        output = _fix_markdown_tables(input_text)
        lines = [l for l in output.split('\n') if l.strip().startswith('|')]
        
        # Should detect 3 columns and split the compressed row
        assert len(lines) >= 4
    
    def test_incomplete_table(self):
        """Handle table that's missing some structure."""
        input_text = """| Metric | Value |
|:---|:---|
| Item1 | $100 |
| Item2 |"""
        
        output = _fix_markdown_tables(input_text)
        
        # Should still output a valid table
        assert '| Item1 | $100 |' in output
        # The incomplete row should be padded
        assert '| Item2 ' in output


class TestTableParsingRealWorld:
    """Real-world examples based on actual Jasper output."""
    
    def test_apple_financials_compressed(self):
        """Real example: Apple financials from LLM with compression."""
        input_text = """| Metric | FY2024 Value |
|:---|:---|
| Net Sales | $391.035B | | Gross Margin % | 46.6% |
| Operating Income | $125.101B | | Operating Margin % | 32% |
| Net Income | $93.7366B | | EPS (Diluted) | $6.05 |"""
        
        output = _fix_markdown_tables(input_text)
        
        # Should decompress into proper rows
        assert '$391.035B' in output
        assert '46.6%' in output
        assert '$125.101B' in output
        assert '32%' in output
        assert '$93.7366B' in output
        assert '$6.05' in output
    
    def test_quarterly_comparison_compressed(self):
        """Real example: Quarterly comparison with compression."""
        input_text = """| Quarter | Revenue | YoY Growth |
|:---|:---|:---|
| Q1 2024 | $120.3B | 12.5% | | Q2 2024 | $135.2B | 18.3% |"""
        
        output = _fix_markdown_tables(input_text)
        
        assert '$120.3B' in output
        assert '12.5%' in output
        assert '$135.2B' in output
        assert '18.3%' in output


class TestCliBoxTableFormatting:
        """Tests for markdown-to-box-table rendering used by CLI reports."""

        def test_markdown_table_transforms_to_box_table(self):
                input_text = """| Metric | Value |
|:---|:---|
| Revenue | $391.035B |
| Gross Margin | 46.6% |"""

                output = _format_cli_markdown(input_text)

                assert '┌' in output
                assert '┐' in output
                assert '│' in output
                assert '└' in output
                assert '$391.035B' in output
                assert '46.6%' in output

        def test_non_table_text_stays_readable(self):
                input_text = """Executive Summary

| Metric | Value |
|:---|:---|
| Revenue | $100B |

Recommendations: Maintain watchlist."""

                output = _format_cli_markdown(input_text)

                assert 'Executive Summary' in output
                assert 'Recommendations: Maintain watchlist.' in output
                assert '$100B' in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
