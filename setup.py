from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="n3mo",
    version="1.0.0",
    description="N3MO: The Impact Tracker",
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