""" For installing package. See LICENSE
"""
from setuptools import setup, find_packages


def load_description():
    """Return description"""
    with open("README.md") as buffer:
        return buffer.read()


def load_version():
    """Return the version number"""
    with open("VERSION") as buffer:
        return buffer.readline().strip()


setup(
    name="classyjson",
    version=load_version(),
    author="Dylan Gregersen",
    author_email="an.email0101@gmail.com",
    url="https://github.com/earthastronaut/classyjson",
    license="MIT",
    description="Wrap jsonschema in python classes",
    long_description=load_description(),
    python_requires=">=3.5",
    packages=find_packages(),
    extra_requires={
        # add schema validation
        "jsonschema": ["jsonschema"],
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
    ],
)
