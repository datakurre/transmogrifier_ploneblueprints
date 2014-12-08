# -*- coding: utf-8 -*-
import posixpath


# collective/transmogrifier/utils.py
# by rpatterson

def pathsplit(path, ospath=posixpath):
    dirname, basename = ospath.split(path)
    if dirname == ospath.sep:
        yield dirname
    elif dirname:
        for elem in pathsplit(dirname):
            yield elem
        yield basename
    elif basename:
        yield basename


# collective/transmogrifier/utils.py
# by rpatterson

def traverse(context, path, default=None):
    """Resolve an object without acquisition or views
    """
    for element in pathsplit(path.strip(posixpath.sep)):
        if not hasattr(context, '_getOb'):
            return default
        context = context._getOb(element, default=default)
        if context is default:
            break
    return context
