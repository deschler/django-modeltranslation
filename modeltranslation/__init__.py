# -*- coding: utf-8 -*-
VERSION = (0, 4, 0, 'beta', 2)


def get_version(version=None, pep386=True, short=False):
    """
    Derives a version number as string from VERSION.

    If the ``pep386`` parameter is ``True`` (default) the returned version will
    be PEP386-compliant (e.g. 0.4.0c1), else the release style naming
    will be used (e.g. 0.4.0-rc1).

    If the ``short`` parameter is ``True``, the release style naming version
    will omit the patch level and sub (e.g. 0.4). The is for example used for
    sphinx.
    """
    if version is None:
        version = VERSION
    assert len(version) == 5
    assert version[3] in ('alpha', 'beta', 'rc', 'final')

    if pep386:
        # Now build the two parts of the version number:
        # main = X.Y[.Z]
        # sub = {a|b|c}N - for alpha, beta and rc releases
        parts = 2 if version[2] == 0 else 3
        main = '.'.join(str(x) for x in version[:parts])
        sub = ''
        if version[3] == 'alpha' and version[4] == 0:
            sub = 'a%d' % (version[4])
        elif version[3] != 'final':
            mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
            sub = mapping[version[3]] + str(version[4])
        return main + sub

    if short:
        return '%d.%d'.format(version[0], version[1])
    return '%d.%d.%d-%s%d' % (
        version[0], version[1], version[2], version[3], version[4])


__version__ = get_version()
