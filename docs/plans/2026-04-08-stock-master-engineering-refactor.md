# Stock Master Engineering Refactor Plan

> For Hermes: implement this plan with TDD where behavior changes, keep package runnable throughout, and verify with the full test suite at the end.

**Goal:** Convert `stock-master` from an ad-hoc `scripts/` layout into a standard Python package with mandatory Python dependencies.

**Architecture:** Introduce a `src/stock_master/` package containing datasource, analysis, and common modules. Keep thin compatibility wrappers under `scripts/` so the skill docs and existing entrypoints still work, but move all real code into the package. Remove optional Python dependency handling for provider modules and declare required dependencies directly in `pyproject.toml`.

**Tech Stack:** setuptools, src-layout packaging, unittest/pytest-compatible test suite, console-script entry points.

---

### Task 1: Create target package skeleton
- Create `src/stock_master/`, `src/stock_master/datasource/`, `src/stock_master/datasource/providers/`, `src/stock_master/analysis/`, `src/stock_master/common/`.
- Add `__init__.py` files and package exports.

### Task 2: Move implementation modules into package namespace
- Move existing code from `scripts/datasource`, `scripts/stock_analysis`, and `scripts/stock_common` into the new package.
- Update imports to use `stock_master.*` package paths.

### Task 3: Preserve CLI compatibility
- Add packaged CLI entry modules for diagnostics and analysis.
- Keep `scripts/data_source.py` and `scripts/analyze_stock.py` as thin wrappers delegating to package entry points.
- Add `[project.scripts]` console scripts in `pyproject.toml`.

### Task 4: Remove optional Python dependency behavior
- Simplify provider loading so `akshare`, `adata`, and `baostock` are normal required imports.
- Remove `MissingDependencyProvider` placeholder flow and tests that only existed for optional dependency handling.
- Keep runtime fallback across providers, but not dependency-based lazy imports.

### Task 5: Normalize packaging metadata
- Expand `pyproject.toml` with standard project metadata, package discovery, dependency declarations, and test config.
- Add a practical `README.md` with install, test, and CLI usage.

### Task 6: Update tests to package imports
- Remove `tests/support.py` path injection.
- Update tests to import from `stock_master.*`.
- Keep live tests gated by env vars.

### Task 7: Verify end-to-end
- Run the full unit test suite.
- Run packaged CLIs using `python -m` and the compatibility wrappers.
- Confirm diagnostics and analysis commands still work.
