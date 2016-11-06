# -*- coding: utf-8 -*-
from Acquisition import aq_base
from plone import api

import base64
import email
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


_marker = object()


def resolve_object(context, item, object_key='_object', uuid_key='_uuid',
                   path_key='_path', default=_marker):
    """Helper for resolving object item using various methods"""
    # 1) cached object
    obj = item.get(object_key)
    try:
        assert aq_base(obj).portal_type is not None
        return obj
    except (AttributeError, AssertionError):
        pass

    # 2) by uuid
    uuid = item.get(uuid_key)
    obj = uuid and api.content.get(UID=uuid)
    if obj is not None:
        return obj

    # 3) by path
    path = item.get(path_key)
    assert path

    obj = traverse(context, path)
    try:
        assert aq_base(obj).portal_type is not None
        return obj
    except (AttributeError, AssertionError):
        pass

    # 4a) raise exception
    if default is _marker:
        raise Exception('{0:s} not found'.format(path))

    # 4b) return default
    return default


def string_to_message(item):
    message = email.message_from_string(item)
    # convert list format
    for k, v in message.items():
        if '\r\n' in v:
            value = v.replace('\r\n  ', '||')
            message.replace_header(k, value)
    return message


def message_to_string(item):
    replacements = []

    # to avoid side effects
    temp_payload = item._payload
    item._payload = base64.decodestring(item._payload)

    for k, v in item.items():
        if '||' in v:
            replacements.append((v, v.replace('||', '\r\n  ')))

    item_as_string = item.as_string(unixfrom=False)

    for replacement in replacements:
        item_as_string = item_as_string.replace(replacement[0], replacement[1])

    item._payload = temp_payload

    return item_as_string
