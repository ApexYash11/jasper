# Jasper Finance v1.1.4 - Release Notes

**Release Date:** March 5, 2026  
**Status:** ✅ Production Ready  
**PyPI:** https://pypi.org/project/jasper-finance/1.1.4/

---

## 🎯 Release Summary

v1.1.4 focuses on **terminal compatibility and output rendering** fixes. This patch addresses a critical issue where ANSI escape codes from Rich's `Live` context manager were visible as green artifacts in VS Code's integrated PowerShell terminal.

### Key Improvements
- ✅ Terminal detection logic for proper ANSI rendering
- ✅ Fallback to plain output in non-TTY environments (VS Code, IDEs)
- ✅ Null-safe Live context updates
- ✅ Maintains full UI in real terminal environments

---

## 🐛 Bug Fixes

### Terminal Output Artifacts Fixed
**Issue:** When running Jasper in VS Code's integrated terminal, visible green horizontal lines appeared before output.

**Root Cause:** Rich's `Live` widget emits ANSI escape codes for cursor control and screen clearing. VS Code's integrated terminal was rendering these codes literally instead of interpreting them.

**Solution:**
```python
# Detect if stdout is a proper TTY
_force_terminal = sys.stdout.isatty()
_force_no_color = not _force_terminal and os.getenv("FORCE_COLOR") != "1"
console = Console(force_terminal=_force_terminal, no_color=_force_no_color)

# Conditional Live rendering
use_live = sys.stdout.isatty() and not os.getenv("TERM") == "dumb"
if use_live:
    live_context = Live(board_panel, refresh_per_second=4, console=console)
else:
    from contextlib import nullcontext
    live_context = nullcontext()
```

### RichLogger Null Safety
- All `self.live.update()` calls now check if `self.live is not None` before executing
- `_should_update_live()` returns `False` immediately if `self.live is None`
- No more AttributeError when Live context is disabled

---

## 🎨 User Experience

### Before v1.1.4
```
╭─────────┐
│         │     ← Green artifact lines visible
│ content │     ← Actual output buried
│         │     ← More green lines
╰─────────╯
```

### After v1.1.4
```
╭─────────┐
│ content │     ← Clean output, no artifacts
│ more... │     ← Properly formatted
╰─────────╯
```

---

## 🔧 Technical Details

### Files Modified
- `jasper/cli/main.py`
  - Added `import sys` for TTY detection
  - Modified console initialization with terminal detection
  - Updated `execute_research()` to conditionally use Live
  - Added null checks in `RichLogger.log()` and `RichLogger.on_synthesis_token()`

### Environment Variables
New optional env var for testing:
- `FORCE_COLOR=1` - Force color output even in non-TTY environments

### Compatibility
- ✅ Real terminals (PowerShell, bash, etc.)
- ✅ VS Code integrated terminal
- ✅ JetBrains IDEs
- ✅ GitHub Actions / CI systems
- ✅ Jupyter notebooks (auto-detection)

---

## 📊 Testing

All existing tests pass:
```
pytest tests/ -v
```

Manual testing completed on:
- PowerShell 7.x
- Windows Terminal
- VS Code integrated terminal
- Real SSH terminal sessions

---

## 🚀 Installation & Upgrade

### Fresh Install
```bash
pip install jasper-finance==1.1.4
```

### Upgrade from v1.1.3
```bash
pip install jasper-finance --upgrade
```

### Docker
```bash
docker build -t jasper-finance:1.1.4 .
docker run -it jasper-finance:1.1.4 ask "What is Apple's revenue?"
```

---

## 🔄 Breaking Changes

**None.** This is a fully backward-compatible patch release.

---

## 📝 Migration Guide

No action required. Simply upgrade and run as normal:

```bash
jasper ask "Your question here"
```

All existing features work identically. The fix is entirely transparent to end users.

---

## 🙏 Acknowledgments

Thanks to the community for reporting the terminal rendering issue. This fix ensures Jasper works seamlessly across all terminal environments.

---

## 📚 Related Issues & PRs

- Issue: Terminal artifacts in VS Code integrated terminal
- Fix: ANSI escape code detection and conditional Live rendering
- Status: ✅ Closed & Resolved

---

## ⏭️ Next Steps

For v1.1.5 and beyond:
- [ ] Performance profiling for large reports
- [ ] Additional data providers (crypto, forex)
- [ ] Streaming report generation
- [ ] API rate limit optimization

---

**Questions?** Visit [GitHub Issues](https://github.com/ApexYash11/jasper/issues) or check the [README](../README.md).
