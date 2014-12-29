# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.

"""
.. note::

   To learn how to implement your own renderer, please analyze the
   source code of the classes defined in this module.

.. note::

   To learn how to register your own renderer (to make it usable with in
   your *n6sdk*-based application), please consult the
   :func:`n6sdk.pyramid_commons.register_stream_renderer` documentation.
"""


import json
import datetime


class BaseStreamRenderer(object):

    """
    The base class for renderers.
    """

    content_type = None

    def __init__(self, data_generator, request):
        if self.content_type is None:
            raise NotImplementedError
        self.data_generator = data_generator
        self.request = request
        self.is_first = True

    def before_content(self, **kwargs):
        return ""

    def after_content(self, **kwargs):
        return ""

    def render_content(self, data, **kwargs):
        raise NotImplementedError

    def iter_content(self, **kwargs):
        for data in self.data_generator:
            yield self.render_content(data)
            self.is_first = False

    def generate_content(self, **kwargs):
        yield self.before_content()
        for content in self.iter_content():
            yield content
        yield self.after_content()
        self.is_first = True


class StreamRenderer_sjson(BaseStreamRenderer):

    """
    The class of the renderer registered as the ``json`` one.
    """

    content_type = "text/plain"

    def render_content(self, data, **kwargs):
        jsonized = json.dumps(dict_with_nulls_removed(data), default=_json_default)
        return jsonized + "\n"


class StreamRenderer_json(BaseStreamRenderer):

    """
    The class of the renderer registered as the ``sjson`` one.
    """

    content_type = "application/json"

    def before_content(self, **kwargs):
        return "[\n"

    def after_content(self, **kwargs):
        return "\n]"

    def render_content(self, data, **kwargs):
        jsonized = json.dumps(
            dict_with_nulls_removed(data),
            default=_json_default,
            indent=4)
        if self.is_first:
            return jsonized
        else:
            return ",\n" + jsonized


#
# Helper functions

def _json_default(o):
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    raise TypeError(repr(o) + " is not JSON serializable")


# helper for dict_with_nulls_removed() (see below)
def _container_with_nulls_removed(
        obj,
        _isinstance=isinstance,
        _jsonable_container=(dict, list, tuple),
        _dict=dict,
        _dict_items=dict.iteritems,
        __quick_cell=[]):
    #assert _isinstance(obj, _jsonable_container)
    try:
        this_func = __quick_cell[0]
    except IndexError:
        # only on the first call:
        __quick_cell.append(_container_with_nulls_removed)
        this_func = __quick_cell[0]
    if _isinstance(obj, _dict):
        items = [
            (k, (this_func(v)
                 if _isinstance(v, _jsonable_container)
                 else (v if (v or v == 0) else None)))
            for k, v in _dict_items(obj)]
        obj = {k: v for k, v in items if v is not None}
    else:
        #assert _isinstance(obj, (list, tuple))
        items = [(this_func(v)
                  if _isinstance(v, _jsonable_container)
                  else (v if (v or v == 0) else None))
                 for v in obj]
        obj = [v for v in items if v is not None]
    if obj:
        return obj
    return None


# optimized + slightly fixed version of previously used _remove_nulls();
# this version is elegamnt and DRY but faster
# [profiling proved that it may be worth do optimize it]
def dict_with_nulls_removed(
        d,
        _container_with_nulls_removed=_container_with_nulls_removed,
        _isinstance=isinstance,
        _jsonable_container=(dict, list, tuple),
        _dict_items=dict.iteritems):
    """
    Get a copy of the given dictionary with empty-or-:obj:`None` items
    removed recursively.

    (A helper function used by the :class:`StreamRenderer_json` and
    :class:`StreamRenderer_sjson` renderers.)

    .. note::

       Values equal to `0` (including :obj:`False`) are *not* removed.
       Other false values -- such as empty sequences (including strings)
       or :obj:`None` -- *are* removed.

    >>> d = {
    ...  'a': 'A', 'b': '', 'c': [], 'd': (), 'e': {}, 'f': [''], 'g': ['x'],
    ...  'h': {
    ...   'a': 'A', 'b': '', 'c': [], 'd': (), 'e': {}, 'f': [''], 'g': ['x'],
    ...  },
    ...  'i': ['A', '', 0, [], (), {}, [None], [0.0], ['x']],
    ...  'j': ['', [{}], ([{}]), {'x': ()}, ['']],
    ...  'k': [None],
    ...  'l': {'x': None},
    ...  'm': None,
    ...  'x': [0],
    ...  'y': {'x': False},
    ...  'z': 0,
    ... }
    >>> d2 = dict_with_nulls_removed(d)
    >>> d2 == {
    ...  'a': 'A', 'g': ['x'],
    ...  'h': {'a': 'A', 'g': ['x']},
    ...  'i': ['A', 0, [0.0], ['x']],
    ...  'x': [0],
    ...  'y': {'x': False},
    ...  'z': 0,
    ... }
    True

    >>> dict_with_nulls_removed({})
    {}
    """
    #assert _isinstance(d, dict)
    items = [
        (k, (_container_with_nulls_removed(v)
             if _isinstance(v, _jsonable_container)
             else (v if (v or v == 0) else None)))
        for k, v in _dict_items(d)]
    return {k: v for k, v in items if v is not None}
