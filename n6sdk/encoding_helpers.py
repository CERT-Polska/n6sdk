# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.
#
# For some parts of the source code of the provide_surrogateescape() function:
# Copyright (c) 2011-2013 Victor Stinner. All rights reserved.
# (For more information -- see the provide_surrogateescape()'s docstring.)


class AsciiMixIn(object):

    r"""
    A mix-in class that provides the :meth:`__str__`, :meth:`__unicode__`
    and :meth:`__format__` special methods based on :func:`ascii_str`.

    >>> class SomeBase(object):
    ...     def __str__(self):
    ...         return 'Cośtam-cośtam'
    ...     def __format__(self, fmt):
    ...         return 'Nó i ' + fmt
    ...
    >>> class MyClass(AsciiMixIn, SomeBase):
    ...     pass
    ...
    >>> obj = MyClass()

    >>> str(obj)
    'Co\\u015btam-co\\u015btam'
    >>> unicode(obj)
    u'Co\\u015btam-co\\u015btam'
    >>> format(obj)
    'N\\xf3 i '

    >>> 'Oto {0:ś}'.format(obj)
    'Oto N\\xf3 i \\u015b'
    >>> u'Oto {0:\\u015b}'.format(obj)  # unicode format string
    u'Oto N\\xf3 i \\u015b'
    >>> 'Oto {0!s}'.format(obj)
    'Oto Co\\u015btam-co\\u015btam'

    >>> 'Oto %s' % obj
    'Oto Co\\u015btam-co\\u015btam'
    >>> u'Oto %s' % obj                 # unicode format string
    u'Oto Co\\u015btam-co\\u015btam'
    """

    def __str__(self):
        return ascii_str(super(AsciiMixIn, self).__str__())

    def __unicode__(self):
        try:
            super_meth = super(AsciiMixIn, self).__unicode__
        except AttributeError:
            super_meth = super(AsciiMixIn, self).__str__
        return ascii_str(super_meth()).decode('ascii')

    def __format__(self, fmt):
        return ascii_str(super(AsciiMixIn, self).__format__(ascii_str(fmt)))


def ascii_str(obj):

    r"""
    Safely convert the given object to an ASCII-only string.

    This function does its best to obtain a pure-ASCII string
    representation (possibly :class:`str`/:func:`unicode`-like, though
    :func:`repr` can also be used as the last-resort fallback) -- *not
    raising* any encoding/decoding exceptions.

    The result is an ASCII str, with non-ASCII characters escaped using
    Python literal notation (``\x...``, ``\u...``, ``\U...``).

    >>> ascii_str('')
    ''
    >>> ascii_str(u'')
    ''
    >>> ascii_str('Ala ma kota\nA kot?\n2=2 ')   # pure ASCII str => unchanged
    'Ala ma kota\nA kot?\n2=2 '
    >>> ascii_str(u'Ala ma kota\nA kot?\n2=2 ')
    'Ala ma kota\nA kot?\n2=2 '

    >>> ascii_str(ValueError('Ech, ale błąd!'))  # UTF-8 str => decoded
    'Ech, ale b\\u0142\\u0105d!'
    >>> ascii_str(ValueError(u'Ech, ale b\u0142\u0105d!'))
    'Ech, ale b\\u0142\\u0105d!'

    >>> ascii_str('\xee\xdd \t jaźń')  # non-UTF-8 str => using surrogateescape
    '\\udcee\\udcdd \t ja\\u017a\\u0144'
    >>> ascii_str(u'\udcee\udcdd \t ja\u017a\u0144')
    '\\udcee\\udcdd \t ja\\u017a\\u0144'

    >>> class Nasty(object):
    ...     def __str__(self): raise UnicodeError
    ...     def __unicode__(self): raise UnicodeError
    ...     def __repr__(self): return 'really nas\xc5\xa7y! \xaa'
    ...
    >>> ascii_str(Nasty())
    'really nas\\u0167y! \\udcaa'
    """

    if not isinstance(obj, unicode):
        try:
            s = str(obj)
        except ValueError:
            try:
                obj = unicode(obj)
            except ValueError:
                obj = repr(obj).decode('utf-8', 'surrogateescape')
        else:
            obj = s.decode('utf-8', 'surrogateescape')
    return obj.encode('ascii', 'backslashreplace')


def as_unicode(obj):

    r"""
    Convert the given object to a :class:`unicode` string.

    Unlike :func:`ascii_str`, this function is not decoding-error-proof and
    does not apply any escaping.

    The function requires that the given object is one of the following:

    * a :class:`unicode` string,
    * a UTF-8-decodable :class:`str` string,
    * an object that produces one of the above kinds of strings when
      converted using :class:`unicode` or :class:`str`, or :func:`repr`
      (the conversions are tried in this order);

    if not -- :exc:`~exceptions.UnicodeDecodeError` is raised.

    >>> as_unicode(u'')
    u''
    >>> as_unicode('')
    u''

    >>> as_unicode(u'O\u0142\xf3wek') == u'O\u0142\xf3wek'
    True
    >>> as_unicode('O\xc5\x82\xc3\xb3wek') == u'O\u0142\xf3wek'
    True
    >>> as_unicode(ValueError(u'O\u0142\xf3wek')) == u'O\u0142\xf3wek'
    True
    >>> as_unicode(ValueError('O\xc5\x82\xc3\xb3wek')) == u'O\u0142\xf3wek'
    True

    >>> class Hard(object):
    ...     def __str__(self): raise UnicodeError
    ...     def __unicode__(self): raise UnicodeError
    ...     def __repr__(self): return 'foo'
    ...
    >>> as_unicode(Hard())
    u'foo'

    >>> as_unicode('\xdd')  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      ...
    UnicodeDecodeError: ...
    """

    if isinstance(obj, str):
        u = obj.decode('utf-8')
    else:
        try:
            u = unicode(obj)
        except ValueError:
            try:
                u = str(obj).decode('utf-8')
            except ValueError:
                u = repr(obj).decode('utf-8')
    return u


def provide_surrogateescape():

    r"""
    Provide the ``surrogateescape`` error handler for bytes-to-unicode
    decoding.

    The source code of the function has been copied from
    https://bitbucket.org/haypo/misc/src/d76f4ff5d27c746c883d40160c8b4fb0891e79f2/python/surrogateescape.py?at=default
    and then adjusted, optimized and commented.  Original code was created by
    Victor Stinner and released by him under the Python license and the BSD
    2-clause license.

    The ``surrogateescape`` error handler is provided out-of-the-box in
    Python 3 but not in Python 2.  It can be used to convert arbitrary
    binary data to Unicode in a practically non-destructive way.

    .. seealso::

       https://www.python.org/dev/peps/pep-0383.

    This implementation (for Python 2) covers only the decoding part of
    the handler, i.e. the :class:`str`-to-:class:`unicode` conversion.
    The encoding (:class:`unicode`-to-:class:`str`) part is not
    implemented.  Note, however, that once we transformed a binary data
    into a *surrogate-escaped* Unicode data we can (in Python 2) freely
    encode/decode it (:class:`unicode`-to/from-:class:`str`), not using
    ``surrogateescape`` anymore, e.g.:

    >>> # We assume that the function has already been called --
    >>> # as it is imported and called in N6SDK/n6sdk/__init__.py
    >>> b = 'ołówek \xee\xdd'          # utf-8 text + some non-utf-8 mess
    >>> b
    'o\xc5\x82\xc3\xb3wek \xee\xdd'
    >>> u = b.decode('utf-8', 'surrogateescape')
    >>> u
    u'o\u0142\xf3wek \udcee\udcdd'
    >>> b2 = u.encode('utf-8')
    >>> b2                             # now all stuff is utf-8 encoded
    'o\xc5\x82\xc3\xb3wek \xed\xb3\xae\xed\xb3\x9d'
    >>> u2 = b2.decode('utf-8')
    >>> u2 == u
    True

    >>> u.encode('latin2',             # doctest: +IGNORE_EXCEPTION_DETAIL
    ...          'surrogateescape')    # does not work for *encoding*
    Traceback (most recent call last):
      ...
    TypeError: don't know how to handle UnicodeEncodeError in error callback

    This function is idempotent (i.e., it can be called safely multiple
    times -- because if the handler is already registered the function
    does not try to register it again) though it is not thread-safe
    (typically it does not matter as the function is supposed to be
    called somewhere at the begginning of program execution).

    .. note::

       This function is called automatically on first import of
       :mod:`n6sdk` module or any of its submodules.

    .. warning::

       In Python 3 (if you were using a Python-3-based application or
       script to handle data produced with Python 2), the ``utf-8``
       codec (as well as other ``utf-...`` codecs) does not decode
       *surrogate-escaped* data encoded to bytes with the Python 2's
       ``utf-8`` codec unless the ``surrogatepass`` error handler is
       used for decoding (on the Python 3 side).

    """

    def surrogateescape(exc,
                        # to avoid namespace dict lookups:
                        isinstance=isinstance,
                        UnicodeDecodeError=UnicodeDecodeError,
                        ord=ord,
                        unichr=unichr,
                        unicode_join=u''.join):
        if isinstance(exc, UnicodeDecodeError):
            decoded = []
            append_to_decoded = decoded.append
            for ch in exc.object[exc.start:exc.end]:
                code = ord(ch)
                if 0x80 <= code <= 0xFF:
                    append_to_decoded(unichr(0xDC00 + code))
                elif code <= 0x7F:
                    append_to_decoded(unichr(code))
                else:
                    raise exc
            decoded = unicode_join(decoded)
            return (decoded, exc.end)
        else:
            raise TypeError("don't know how to handle {} in error callback"
                            .format(type(exc).__name__))
    import codecs
    try:
        codecs.lookup_error('surrogateescape')
    except LookupError:
        codecs.register_error('surrogateescape', surrogateescape)
