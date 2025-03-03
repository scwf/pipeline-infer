from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pipeline-infer",
    version="0.1.0",
    description="高效的CV流水线并发推理框架",
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
            "mypy>=0.900",
            "types-Pillow>=8.0.0",
            "flake8>=3.9.0",
            "black>=21.0.0",
            "isort>=5.0.0",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt"],
    },
) 