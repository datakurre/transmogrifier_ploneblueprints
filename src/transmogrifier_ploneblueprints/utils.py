# -*- coding: utf-8 -*-
import Acquisition
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

# noinspection PyProtectedMember,PyUnresolvedReferences
def explicit_traverse(context, path, default=None):
    """Resolve an object without acquisition or views
    """
    for element in pathsplit(path.strip(posixpath.sep)):
        try:
            base = Acquisition.aq_base(context)
            context = base._getOb(element, default=default)
        except AttributeError:
            return default
        if context is default:
            break
    return context


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
