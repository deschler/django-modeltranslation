#!/usr/bin/env python
import sys

version = sys.argv[1]
if version.startswith("http"):
    print(version)
else:
    next_version = version[:-1] + "%d" % (int(version[-1]) + 1)
    print("Django>=%s,<%s" % (version, next_version))
