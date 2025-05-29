import os
from setuptools import setup, find_packages

# Read the contents of README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = []
    for line in f:
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue
        # Skip git+ dependencies for PyPI compatibility
        if line.startswith("git+"):
            # Git dependencies aren't directly supported by PyPI
            # They'll be handled through extras_require
            continue

        requirements.append(line)

setup(
    name="turbodesigner",
    version="1.0.0",
    author="Open Orion, Inc.",
    description="An open-source turbomachinery designer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OpenOrion/turbodesigner",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    include_package_data=True,
    package_data={
        "turbodesigner": ["**/*.json"],
    },
)