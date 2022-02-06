from os import path
from setuptools import setup, find_packages

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="bucketman",
    version="0.2.0",
    description="A terminal application for working with S3 buckets.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "boto3",
        "click",
        "textual",
    ],
    extras_require={"dev": {"autopep8", "pylint", "keepachangelog", "wheel"}},
    entry_points="""
        [console_scripts]
        bucketman=bucketman.cli:main
    """,
)
