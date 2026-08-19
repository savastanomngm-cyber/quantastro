from setuptools import setup, find_packages

setup(
    name="astroquant",
    version="0.1.0",
    description="Quantitative astro-trading signal engine",
    packages=find_packages(),
    install_requires=["pyswisseph>=2.10", "numpy>=1.21", "pandas>=1.3"],
    extras_require={"dev": ["pytest>=7.0"]},
    python_requires=">=3.9",
)