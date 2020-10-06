#!/usr/bin/env python3
# pylint: disable=import-outside-toplevel,attribute-defined-outside-init

import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def run_tests(self):
        import shlex
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


def read_file(x):
    with open(x, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield line


install_requires = list(read_file("requirements.txt"))

setup(
    name="jzmq",
    description="just playing around with ØMQ (pyzmq)",
    author="Paul Miller",
    author_email="paul@jettero.pl",
    url="https://github.com/jettero/jzmq-experiments",
    packages=find_packages(),
    cmdclass={"test": PyTest},
    tests_require=["pytest"],
    install_requires=install_requires,
    setup_requires=["setuptools_scm"],
    use_scm_version={
        "write_to": "jzmq/__version__.py",
        "tag_regex": r"^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$",
        # NOTE: use ./setup.py --version to regenerate version.py and print the
        # computed version
    },
    entry_points={
        "console_scripts": ["jzmq-chat = jzmq.cmd:chat"],
    },
)
