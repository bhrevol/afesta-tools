"""Sphinx configuration."""
project = "Afesta Tools"
author = "byeonhyeok"
copyright = "2022, byeonhyeok"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_click",
]
autodoc_typehints = "description"
html_theme = "furo"
