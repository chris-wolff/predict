"""PREDICT DEMO

This is meant to be a rough outline of how predict is meant to function
"""

from setuptools import setup

setup(
    name="predict",
    packages=["predict"],
    install_requires=["bs4", "flask", "requests"],
    entry_points={
        "console_scripts": ["predict=predict.cli:main"]
    }
)