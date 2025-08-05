#!/usr/bin/env python3
"""
Setup configuration for Komodo DeFi Framework Documentation Tools
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
def read_requirements(filename):
    """Read requirements from file, filtering out comments and empty lines."""
    requirements = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-r'):
                    requirements.append(line)
    except FileNotFoundError:
        pass
    return requirements

# Core requirements
install_requires = read_requirements('requirements.txt')

# Optional requirements for development
dev_requires = [
    'pytest>=7.4.0,<8.0.0',
    'pytest-asyncio>=0.21.0,<1.0.0',
    'pytest-cov>=4.1.0,<5.0.0',
    'black>=23.0.0,<24.0.0',
    'flake8>=6.0.0,<7.0.0',
    'isort>=5.12.0,<6.0.0',
    'mypy>=1.5.0,<2.0.0',
    'pre-commit>=3.4.0,<4.0.0',
]

# Performance requirements
performance_requires = [
    'ujson>=5.8.0,<6.0.0',
    'orjson>=3.9.0,<4.0.0',
    'pydantic>=2.0.0,<3.0.0',
]

# Documentation requirements
docs_requires = [
    'sphinx>=7.1.0,<8.0.0',
    'sphinx-rtd-theme>=1.3.0,<2.0.0',
]

setup(
    name="komodo-defi-docs-tools",
    version="2.0.0",
    author="Komodo Platform",
    author_email="development@komodoplatform.com",
    description="Comprehensive tools for managing Komodo DeFi Framework API documentation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/KomodoPlatform/komodo-docs-mdx",
    packages=find_packages(include=['lib', 'lib.*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Documentation",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires,
        'performance': performance_requires,
        'docs': docs_requires,
        'all': dev_requires + performance_requires + docs_requires,
    },
    entry_points={
        'console_scripts': [
            'kdf-tools=kdf_tools:main',
        ],
    },
    include_package_data=True,
    package_data={
        'lib': ['*.json', '*.yaml', '*.yml'],
    },
    zip_safe=False,
    project_urls={
        "Bug Reports": "https://github.com/KomodoPlatform/komodo-docs-mdx/issues",
        "Source": "https://github.com/KomodoPlatform/komodo-docs-mdx",
        "Documentation": "https://developers.komodoplatform.com/",
    },
) 