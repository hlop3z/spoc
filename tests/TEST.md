# Pytest

## 🔹 **Common Recommended Command**

```bash
pytest -xv --tb=short --disable-warnings
```

| Flag                 | Purpose                                |
| -------------------- | -------------------------------------- |
| `-x`                 | Stop after first failure               |
| `-v`                 | Verbose output                         |
| `--tb=short`         | Short traceback (cleaner error output) |
| `--disable-warnings` | Hide warning clutter                   |

---

## 🔹 **For Full Test Run with Coverage**

```bash
pytest --cov=src --cov-report=term-missing -v
```

Requires `pytest-cov`. Shows missing lines in source coverage.

---

## 🔹 **For Debugging**

```bash
pytest -s --pdb
```

| Flag    | Purpose                                    |
| ------- | ------------------------------------------ |
| `-s`    | Allow `print()` output in terminal         |
| `--pdb` | Drops into interactive debugger on failure |

---

## 🔹 **Parallel Test Execution**

```bash
pytest -n auto
```

Requires `pytest-xdist`. Runs tests in parallel using all available CPUs.

---

## 🔹 **With Configuration File (`pytest.ini`)**

To avoid repeating flags:

```ini
# pytest.ini
[pytest]
addopts = -xv --tb=short --disable-warnings
testpaths = tests
```

Then just run:

```bash
pytest
```
