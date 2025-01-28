from setuptools import setup, find_packages

setup(
    name="traid",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pytest>=8.0.0",
    ],
)
