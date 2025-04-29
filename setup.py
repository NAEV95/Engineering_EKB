from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="promut-md",
    version="0.1.0",
    author="Nick Venanzi",
    author_email="venanzi.nae@gmail.com",
    description="Protein Mutation Effect Prediction using MD Simulations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Naev95/ProMut-MD",
    packages=find_packages(include=["src", "src.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Chemistry",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "promut-md=src.cli:main",
        ],
    },
) 