"""Exclude transitional cloud admin commands from device distributions."""

from setuptools import setup
from setuptools.command.build_py import build_py


class DeviceBuild(build_py):
    def find_package_modules(self, package, package_dir):
        return [
            item
            for item in super().find_package_modules(package, package_dir)
            if not (package == "tools" and item[1] in {"approve_pairing", "revoke_device"})
        ]


setup(cmdclass={"build_py": DeviceBuild})
