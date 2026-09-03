from setuptools import setup, find_packages

setup(
    name="spdc",
    version="0.1",
    author="Ilija Funk",
    packages=find_packages(exclude="layout"),
    include_package_data=True,
)
# package_dir={"": "spdc"}
