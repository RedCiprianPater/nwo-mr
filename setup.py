from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nwo-mr",
    version="0.1.0",
    author="NWO Robotics",
    author_email="ciprian.pater@publicae.org",
    description="Mixed Reality layer for NWO Robotics - enabling AI agents to embody avatars, simulate robotics, and participate in virtual economies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RedCiprianPater/nwo-mr",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "eth-account>=0.8.0",
        "web3>=6.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.990",
        ],
        "full": [
            "nwo-robotics-cs>=0.1.0",
            "websockets>=10.0",
            "aiohttp>=3.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "nwo-mr=nwo_mr.cli:main",
        ],
    },
)
