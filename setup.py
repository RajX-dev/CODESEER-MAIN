from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="n3mo",
    version="1.0.4",
    description="N3MO: The Impact Tracker",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "n3mo": ["docker-compose.yml", "db/*.sql"],
    },
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'n3mo=n3mo.cli:main',
        ],
    },
)