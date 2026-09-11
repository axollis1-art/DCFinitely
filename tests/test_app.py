"""Smoke tests for the project entry point and package structure."""

from pathlib import Path


def test_streamlit_entry_point_exists() -> None:
    """Keep the documented `streamlit run app.py` command valid."""
    assert Path("app.py").is_file()


def test_core_package_exists() -> None:
    """Keep the initial modular package layout in place."""
    assert Path("src/__init__.py").is_file()
