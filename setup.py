from setuptools import setup, find_packages

setup(
    name = "dw_anki",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'lxml',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'dw_anki = dw_anki.dw_anki:main',
        ],
    }
)
