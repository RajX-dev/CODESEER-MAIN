from setuptools import setup, find_packages

setup(
    name="n3mo",
    version="1.0.0",
    description="N3MO: The Impact Tracker",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'n3mo=n3mo.wrapper:main',
        ],
    },
)