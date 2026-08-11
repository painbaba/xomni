# verify-runner example project

A tiny, deliberately simple project used to exercise the `verify-runner`
plugin end to end. Everything here is stdlib-only and ruff-clean.

| File                 | Purpose                                          |
| -------------------- | ------------------------------------------------ |
| `example_math.py`    | Module with two functions: `add()` and `is_even()` |
| `test_example_math.py` | 4 passing unittest tests (also pytest-compatible) |
| `clean_script.py`    | Standalone ruff-clean script                     |

Verify it from this directory:

```bash
/verify
```

or programmatically:

```python
from verify_runner import verify_project

print(verify_project("plugins/verify-runner/examples"))
```

Expected verdict: `VERDICT: PASS` (4 tests, ruff clean).
