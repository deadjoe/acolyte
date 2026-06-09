"""Acolyte package setup — metadata is in pyproject.toml."""

from setuptools import find_packages, setup

setup(
    name="acolyte",
    packages=find_packages(),
    include_package_data=True,
)
