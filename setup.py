"""
Setup script for AtlasUI.
"""

from setuptools import setup, find_packages

setup(
    packages=find_packages(exclude=["tests", "tests.*", "docs"]),
    package_data={
        "atlasui": [
            "static/**/*",
            "templates/**/*",
        ],
    },
)
