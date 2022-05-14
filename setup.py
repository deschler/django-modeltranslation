#!/usr/bin/env python
import pkg_resources
from setuptools import setup

# (1) check required versions (from https://medium.com/@daveshawley/safely-using-setup-cfg-for-metadata-1babbe54c108)
pkg_resources.require("setuptools>=39.2")

setup()
