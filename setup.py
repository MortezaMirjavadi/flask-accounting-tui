"""Setup configuration for the accounting system."""

from setuptools import setup, find_packages

setup(
    name="accounting-system",
    version="1.0.0",
    description="Terminal-based accounting system with Flask API",
    author="Your Name",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.0.0",
        "Werkzeug>=2.0.0",
        "textual>=0.41.0",
        "requests>=2.28.0",
        "jdatetime>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "accounting-api=run_api:main",
            "accounting-tui=run_tui:main",
        ],
    },
)
