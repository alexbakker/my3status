from setuptools import find_packages, setup
from my3status import __version__

setup(
    name="my3status",
    version=__version__,
    description="A very simple alternative to i3status",
    author="Alexander Bakker",
    author_email="github@alexbakker.me",
    url="https://github.com/alexbakker/my3status",
    packages=find_packages(),
    install_requires=[
        "psutil",
    ],
    extras_require={
        "volume": "pulsectl",
        "net": "requests"
    },
    license="MIT"
)
