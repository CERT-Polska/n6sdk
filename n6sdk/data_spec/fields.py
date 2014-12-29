# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.

"""
.. note::

   For basic information how to use the classes defined in this module
   -- please consult the :ref:`data_spec_class` chapter of the tutorial,
   in particular the :ref:`n6sdk_field_classes` and
   :ref:`custom_field_classes` sections.
"""


import collections
import datetime
import re

from n6sdk.addr_helpers import (
    ip_network_as_tuple,
)
from n6sdk.datetime_helpers import (
    datetime_utc_normalize,
    parse_iso_datetime_to_utc,
)
from n6sdk.encoding_helpers import (
    ascii_str,
    as_unicode,
)
from n6sdk.exceptions import (
    FieldValueError,
    FieldValueTooLongError,
)
from n6sdk.regexes import (
    CC_SIMPLE_REGEX,
    DOMAIN_ASCII_LOWERCASE_REGEX,
    IPv4_STRICT_DECIMAL_REGEX,
    IPv4_CIDR_NETWORK_REGEX,
    IPv4_ANONYMIZED_REGEX,
    SOURCE_REGEX,
)



#
# The base field specification class

class Field(object):

    """
    The base class for all data field specification classes.

    It has two (overridable/extendable) methods:
    :meth:`clean_param_value` and :meth:`clean_result_value`
    (see below).

    Note that fields can be customized in two ways:

    * by subclassing (and overridding/extending some of their
      attributes/methods);

    * by specifying custom per-instance values of any of the
      class-defined attributes -- by passing them as keyword arguments
      to the constructor of a particular class.

    Constructors of all field classes accept the following keyword-only
    arguments:

    * `in_result` (default: :obj:`None`):
          One of: ``'required'``, ``'optional'``, :obj:`None`.
    * `in_params` (default: :obj:`None`:
          One of: ``'required'``, ``'optional'``, :obj:`None`.
    * `single_param` (default: :obj:`False`):
          If false: multiple query parameter values are allowed.
    * `extra_params` (default: :obj:`None`):
          A dictionary that maps parameter *subnames* (second parts of
          *dotted names*) to instances of :class:`Field` or of its
          subclass.
    * `custom_info` (default: an empty dictionary):
          A dictionary containing arbitrary data (accessible as the
          :attr:`custom_info` instance attribute).
    * **any** keyword arguments whose names are the names of class-level
      attributes (see the second point in the paragraph above).
    """

    def __init__(self, **kwargs):
        self._init_kwargs = kwargs
        self._set_public_attrs(**kwargs)

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join(
                '{}={!r}'.format(key, value)
                for key, value in sorted(self._init_kwargs.iteritems())))


    #
    # overridable methods

    def clean_param_value(self, value):
        """
        The method called by *data specification*'s parameter cleaning methods.

        Args:
            `value`:
                A singular parameter value (being *always* a
                :class:`str` or :class:`unicode` instance).

        Returns:
            The value after necessary cleaning (adjustment/coercion/etc.
            and validation).

        Raises:
            Any instance/subclass of :exc:`~exceptions.Exception`,
            (especially a :exc:`n6sdk.exceptions.FieldValueError`).

        The default implementation just passes the value unchanged.
        This method can be extended (using :func:`super`) in subclasses.

        .. note::

           Although any subclass of :exc:`~exceptions.Exception` can be
           used to signalize a cleaning/validation error, if you want to
           specify a *public message*, use
           :exc:`n6sdk.exceptions.FieldValueError` with the
           `public_message` constructor keyword argument specified.
        """
        assert isinstance(value, basestring)
        return value

    def clean_result_value(self, value):
        """
        The method called by *data specification*'s result cleaning methods.

        Args:
            `value`:
                A result item value (*not* necessarily a string;
                valid types depend on a particular implementation of
                the method).

        Returns:
            The value after necessary cleaning (adjustment/coercion/etc.
            and validation).

        Raises:
            Any instance/subclass of :exc:`~exceptions.Exception`.

        The default implementation just passes the value unchanged.
        This method can be extended (using :func:`super`) in subclasses.
        """
        return value


    #
    # non-public internals

    def _set_public_attrs(self,
                          in_result=None,
                          in_params=None,
                          single_param=False,
                          extra_params=None,
                          custom_info=None,
                          **per_instance_attrs):
        self.in_result = self._in_arg_checked(in_result)
        self.in_params = self._in_arg_checked(in_params)
        self.single_param = single_param
        self.extra_params = (
            extra_params if extra_params is not None
            else {})
        self.custom_info = (
            custom_info if custom_info is not None
            else {})
        self._set_per_instance_attrs(per_instance_attrs)

    def _in_arg_checked(self, arg):
        if arg not in (None, 'required', 'optional'):
            raise ValueError("{!r} is not one of: None, 'required', 'optional'"
                             .format(arg))
        return arg

    def _set_per_instance_attrs(self, per_instance_attrs):
        # per-instance customizations of attributes defined in the class body
        cls = self.__class__
        for attr_name, obj in per_instance_attrs.iteritems():
            if hasattr(cls, attr_name):
                setattr(self, attr_name, obj)
            else:
                raise TypeError(
                    '{}.__init__() got an unexpected keyword argument {!r}'
                    .format(cls.__name__, attr_name))

    @staticmethod
    def _split_raw_param_value(raw_value):
        # called in <data spec>._iter_clean_param_items()
        if not isinstance(raw_value, basestring):
            raise TypeError(
                'param values are expected to be strings; got: {!r}'
                .format(raw_value))
        return raw_value.split(',')



#
# Concrete field specification classes

class DateTimeField(Field):

    """
    For date-and-time (timestamp) values, automatically normalized to UTC.
    """

    def clean_param_value(self, value):
        """
        The input `value` should be a :class:`str`/:class:`unicode` string,
        *ISO-8601*-formatted.

        Returns: a :class:`datetime.datetime` object (a *naive* one,
        i.e. not aware of any timezone).
        """
        value = super(DateTimeField, self).clean_param_value(value)
        return self._parse_datetime_string(value)

    def clean_result_value(self, value):
        """
        The input `value` should be a :class:`str`/:class:`unicode` string
        (*ISO-8601*-formatted) or a :class:`datetime.datetime` object
        (timezone-aware or *naive*).

        Returns: a :class:`datetime.datetime` object (a *naive* one,
        i.e. not aware of any timezone).
        """
        value = super(DateTimeField, self).clean_result_value(value)
        if isinstance(value, datetime.datetime):
            return datetime_utc_normalize(value)
        if isinstance(value, basestring):
            return self._parse_datetime_string(value)
        raise TypeError(
            '{!r} is neither a str/unicode nor a '
            'datetime.datetime object'.format(value))

    @staticmethod
    def _parse_datetime_string(value):
        try:
            return parse_iso_datetime_to_utc(value)
        except Exception:
            raise FieldValueError(public_message=(
                u'"{}" is not a valid date + '
                u'time specification'.format(ascii_str(value))))


class UnicodeField(Field):

    """
    For arbitrary text data.
    """

    encoding = 'utf-8'
    decode_error_handling = 'strict'

    def clean_param_value(self, value):
        value = super(UnicodeField, self).clean_param_value(value)
        value = self._fix_value(value)
        self._validate_value(value)
        return value

    def clean_result_value(self, value):
        value = super(UnicodeField, self).clean_result_value(value)
        if not isinstance(value, basestring):
            raise TypeError('{!r} is not a str/unicode instance'.format(value))
        value = self._fix_value(value)
        self._validate_value(value)
        return value

    def _fix_value(self, value):
        if isinstance(value, str):
            try:
                value = value.decode(self.encoding, self.decode_error_handling)
            except UnicodeError:
                raise FieldValueError(public_message=(
                    u'"{}" cannot be decoded with encoding "{}"'.format(
                        ascii_str(value),
                        self.encoding)))
        assert isinstance(value, unicode)
        return value

    def _validate_value(self, value):
        pass


class HexDigestField(UnicodeField):

    """
    For hexadecimal digests (hashes), such as *MD5*, *SHA256* or any other.

    The constructor-arguments-or-subclass-attributes:
    :attr:`num_of_characters` (the exact number of characters each hex
    digest consist of) and :attr:`hash_algo_descr` (the digest algorithm
    label, such as ``"MD5"`` or ``"SHA256"``) are obligatory.
    """

    num_of_characters = None
    hash_algo_descr = None

    def __init__(self, **kwargs):
        super(HexDigestField, self).__init__(**kwargs)
        if self.num_of_characters is None:
            raise TypeError("'num_of_characters' not specified for {} "
                            "(neither as a class attribute nor "
                            "as a constructor argument)"
                            .format(self.__class__.__name__))
        if self.hash_algo_descr is None:
            raise TypeError("'hash_algo_descr' not specified for {} "
                            "(neither as a class attribute nor "
                            "as a constructor argument)"
                            .format(self.__class__.__name__))
        if getattr(self, 'max_length', None) is None:
            self.max_length = self.num_of_characters

    def _fix_value(self, value):
        value = super(HexDigestField, self)._fix_value(value)
        return value.lower()

    def _validate_value(self, value):
        super(HexDigestField, self)._validate_value(value)
        try:
            value.decode('hex')
            if len(value) != self.num_of_characters:
                raise ValueError
        except (TypeError, ValueError):
            raise FieldValueError(public_message=(
                u'"{}" is not a valid {} hash'.format(
                    ascii_str(value),
                    self.hash_algo_descr)))


class MD5Field(HexDigestField):

    """
    For hexadecimal MD5 digests (hashes).
    """

    num_of_characters = 32
    hash_algo_descr = 'MD5'


class SHA1Field(HexDigestField):

    """
    For hexadecimal SHA1 digests (hashes).
    """

    num_of_characters = 40
    hash_algo_descr = 'SHA1'


class UnicodeEnumField(UnicodeField):

    """
    For text data limited to a finite set of possible values.

    The constructor-argument-or-subclass-attribute :attr:`enum_values`
    (a sequence or set of strings) is obligatory.
    """

    enum_values = None

    def __init__(self, **kwargs):
        super(UnicodeEnumField, self).__init__(**kwargs)
        if self.enum_values is None:
            raise TypeError("'enum_values' not specified for {} "
                            "(neither as a class attribute nor "
                            "as a constructor argument)"
                            .format(self.__class__.__name__))
        self.enum_values = tuple(as_unicode(v) for v in self.enum_values)

    def _validate_value(self, value):
        super(UnicodeEnumField, self)._validate_value(value)
        if value not in self.enum_values:
            raise FieldValueError(public_message=(
                u'"{}" is not one of: {}'.format(
                    ascii_str(value),
                    u', '.join(u'"{}"'.format(v) for v in self.enum_values))))


class UnicodeLimitedField(UnicodeField):

    """
    For text data with limited length.

    The constructor-argument-or-subclass-attribute :attr:`max_length`
    (an integer number greater or equal to 1) is obligatory.
    """

    max_length = None

    #: **Experimental attribute**
    #: (can be removed in future versions,
    #: so do not rely on it, please).
    checking_bytes_length = False

    def __init__(self, **kwargs):
        super(UnicodeLimitedField, self).__init__(**kwargs)
        if self.max_length is None:
            raise TypeError("'max_length' not specified for {} "
                            "(neither as a class attribute nor "
                            "as a constructor argument)"
                            .format(self.__class__.__name__))
        if self.max_length < 1:
            raise ValueError("'max_length' specified for {} should "
                             "not be lesser than 1 ({} given)"
                             .format(self.__class__.__name__,
                                     ascii_str(self.max_length)))

    def _validate_value(self, value):
        super(UnicodeLimitedField, self)._validate_value(value)
        if self.checking_bytes_length:
            value = value.encode(self.encoding)
        if len(value) > self.max_length:
            raise FieldValueTooLongError(
                field=self,
                checked_value=value,
                max_length=self.max_length,
                public_message=(
                    u'Length of "{}" is greater than {}'.format(
                        ascii_str(value),
                        self.max_length)))


class UnicodeRegexField(UnicodeField):

    """
    For text data limited by the specified regular expression.

    The constructor-argument-or-subclass-attribute :attr:`regex` (a
    regular expression specified as a string or a compiled regular
    expression object) is obligatory.
    """

    regex = None
    error_msg_template = u'"{}" is not a valid value'

    def __init__(self, **kwargs):
        super(UnicodeRegexField, self).__init__(**kwargs)
        if self.regex is None:
            raise TypeError("'regex' not specified for {} "
                            "(neither as a class attribute "
                            "nor as a constructor argument)"
                            .format(self.__class__.__name__))
        if isinstance(self.regex, basestring):
            self.regex = re.compile(self.regex)

    def _validate_value(self, value):
        super(UnicodeRegexField, self)._validate_value(value)
        if self.regex.search(value) is None:
            raise FieldValueError(public_message=(
                self.error_msg_template.format(ascii_str(value))))


class SourceField(UnicodeLimitedField, UnicodeRegexField):

    """
    For dot-separated source specifications, such as ``my-org.type``.
    """

    regex = SOURCE_REGEX
    error_msg_template = '"{}" is not a valid source specification'
    max_length = 32


class IPv4Field(UnicodeLimitedField, UnicodeRegexField):

    """
    For IPv4 addresses, such as ``127.234.5.17``.

    (Using decimal dotted-quad notation.)
    """

    regex = IPv4_STRICT_DECIMAL_REGEX
    error_msg_template = '"{}" is not a valid IPv4 address'
    max_length = 15  # <- formally redundant but improves introspection


class AnonymizedIPv4Field(UnicodeLimitedField, UnicodeRegexField):

    """
    For anonymized IPv4 addresses, such as ``x.x.5.17``.

    (Using decimal dotted-quad notation, with the leftmost octet -- and
    possibly any other octets -- replaced with "x".)
    """

    regex = IPv4_ANONYMIZED_REGEX
    error_msg_template = '"{}" is not a valid anonymized IPv4 address'
    max_length = 13  # <- formally redundant but improves introspection

    def _fix_value(self, value):
        value = super(AnonymizedIPv4Field, self)._fix_value(value)
        return value.lower()


class IPv4NetField(UnicodeLimitedField, UnicodeRegexField):

    """
    For IPv4 network specifications (CIDR), such as ``127.234.5.0/24``.
    """

    regex = IPv4_CIDR_NETWORK_REGEX
    error_msg_template = ('"{}" is not a valid CIDR '
                          'IPv4 network specification')
    max_length = 18  # <- formally redundant but improves introspection

    def clean_param_value(self, value):
        value = super(IPv4NetField, self).clean_param_value(value)
        ip, net = ip_network_as_tuple(value)
        assert isinstance(ip, unicode) and IPv4_STRICT_DECIMAL_REGEX.search(ip)
        assert isinstance(net, int) and 0 <= net <= 32
        # returning tuple: ip is a unicode string, net is an int number
        return ip, net

    def clean_result_value(self, value):
        if not isinstance(value, basestring):
            try:
                ip, net = value
                value = '{}/{}'.format(ip, net)
            except (ValueError, TypeError):
                raise FieldValueError(public_message=(
                    self.error_msg_template.format(ascii_str(value))))
        # returning unicode string
        return super(IPv4NetField, self).clean_result_value(value)


class CCField(UnicodeLimitedField, UnicodeRegexField):

    """
    For 2-letter country codes, such as ``FR`` or ``UA``.
    """

    regex = CC_SIMPLE_REGEX
    error_msg_template = '"{}" is not a valid 2-character country code'
    max_length = 2   # <- formally redundant but improves introspection

    def _fix_value(self, value):
        value = super(CCField, self)._fix_value(value)
        return value.upper()


class URLSubstringField(UnicodeLimitedField):

    """
    For substrings of URLs (such as ``xample.com/path?que``).
    """

    max_length = 2048
    decode_error_handling = 'surrogateescape'


class URLField(URLSubstringField):

    """
    For URLs (such as ``http://xyz.example.com/path?query=foo#fr``).
    """


class DomainNameSubstringField(UnicodeLimitedField):

    """
    For substrings of domain names, automatically IDNA-encoded and lower-cased.
    """

    max_length = 255

    def _fix_value(self, value):
        value = super(DomainNameSubstringField, self)._fix_value(value)
        try:
            ascii_value = value.encode('idna')
        except ValueError:
            raise FieldValueError(public_message=(
                u'"{}" could not be encoded using the '
                u'IDNA encoding'.format(ascii_str(value))))
        return unicode(ascii_value.lower())


class DomainNameField(DomainNameSubstringField, UnicodeRegexField):

    """
    For domain names, automatically IDNA-encoded and lower-cased.
    """

    regex = DOMAIN_ASCII_LOWERCASE_REGEX
    error_msg_template = '"{}" is not a valid domain name'


class IntegerField(Field):

    """
    For integer numbers (optionally with min./max. limits defined).
    """

    min_value = None
    max_value = None
    error_msg_template = None

    def clean_param_value(self, value):
        value = super(IntegerField, self).clean_param_value(value)
        return self._clean_value(value)

    def clean_result_value(self, value):
        value = super(IntegerField, self).clean_result_value(value)
        return self._clean_value(value)

    def _clean_value(self, value):
        try:
            value = self._coerce_value(value)
            self._check_range(value)
        except FieldValueError:
            if self.error_msg_template is None:
                raise
            raise FieldValueError(public_message=(
                self.error_msg_template.format(ascii_str(value))))
        return value

    def _coerce_value(self, value):
        try:
            coerced_value = self._do_coerce(value)
            # e.g. float is OK *only* if it is an integer number (such as 42.0)
            if not isinstance(value, basestring) and coerced_value != value:
                raise ValueError
        except (TypeError, ValueError):
            raise FieldValueError(public_message=(
                u'"{}" cannot be interpreted as an '
                u'integer number'.format(ascii_str(value))))
        assert isinstance(coerced_value, (int, long))  # long if > sys.maxint
        return coerced_value

    def _do_coerce(self, value):
        return int(value)

    def _check_range(self, value):
        assert isinstance(value, (int, long))
        if self.min_value is not None and value < self.min_value:
            raise FieldValueError(public_message=(
                u'{} is lesser than {}'.format(value, self.min_value)))
        if self.max_value is not None and value > self.max_value:
            raise FieldValueError(public_message=(
                u'{} is greater than {}'.format(value, self.max_value)))


class ASNField(IntegerField):

    """
    For AS numbers, such as ``12345``, ``123456789`` or ``12345.65432``.
    """

    min_value = 0
    max_value = 2 ** 32 - 1
    error_msg_template = '"{}" is not a valid Autonomous System Number'

    def _do_coerce(self, value):
        # supporting also the '<16-bit number>.<16-bitnumber>' ASN notation
        if isinstance(value, basestring):
            if '.' in value:
                high, low = map(int, value.split('.'))
                if not (0 <= low <= 65535):  # (high is checked later)
                    raise ValueError
                return (high << 16) + low
            else:
                return int(value)
        elif isinstance(value, (int, long)):
            return int(value)
        else:
            # not accepting e.g. floats, to avoid the '42.0'/42.0-confusion
            # ('42.0' gives 42 * 2**16 but 42.0 would give 42 if were accepted)
            raise TypeError


class PortField(IntegerField):

    """
    For TCP/UDP port numbers, such as ``12345``.
    """

    min_value = 0
    max_value = 2 ** 16 - 1
    error_msg_template = '"{}" is not a valid port number'


class ResultListFieldMixin(Field):

    """
    A mix-in class for fields whose result values are supposed to be
    a *sequence of values* and not single values.

    Its :meth:`clean_result_value` checks that its argument is a
    *non-string sequence* (:class:`list` or :class:`tuple`, or any other
    :class:`collections.Sequence` not being :class:`str` or
    :class:`unicode`) and performs result cleaning (as defined in a
    superclass) for *each item* of it.

    See: :class:`AddressField` below.
    """

    allow_empty = False

    def clean_result_value(self, value):
        if isinstance(value, basestring) or (
              not isinstance(value, collections.Sequence)):
            raise TypeError('{!r} is not a non-string sequence'.format(value))
        if not self.allow_empty and not value:
            raise ValueError('empty sequence given')
        do_clean = super(ResultListFieldMixin, self).clean_result_value
        return self._clean_result_list(value, do_clean)

    def _clean_result_list(self, value, do_clean):
        checked_value_list = []
        too_long = False
        for v in value:
            try:
                v = do_clean(v)
            except FieldValueTooLongError as exc:
                if exc.field is not self:
                    raise
                too_long = True
                assert hasattr(self, 'max_length')
                assert exc.max_length == self.max_length
                v = exc.checked_value
            checked_value_list.append(v)
        if too_long:
            raise FieldValueTooLongError(
                field=self,
                checked_value=checked_value_list,
                max_length=self.max_length,
                public_message=(
                    u'Length of at least one item of '
                    u'list {} is greater than {}'.format(
                        ascii_str(value),
                        self.max_length)))
        return checked_value_list


class DictResultField(Field):

    """
    A base class for fields whose result values are supposed to be
    dictionaries (whose fixed structure is defined by
    :attr:`key_to_subfield_factory` and :attr:`required_keys`).

    The constructor-argument-or-subclass-attribute
    :attr:`key_to_subfield_factory` (a dictionary that maps subfield
    names to subfield factories or classes) is obligatory.
    """

    key_to_subfield_factory = None
    required_keys = frozenset()

    def __init__(self, **kwargs):
        super(DictResultField, self).__init__(**kwargs)
        if self.key_to_subfield_factory is None:
            raise TypeError(
                  "'key_to_subfield_factory' not specified for {} (neither "
                  "as a class attribute nor as a constructor argument)"
                  .format(self.__class__.__name__))
        self.key_to_subfield = {
            key.decode('ascii'): factory()
            for key, factory in self.key_to_subfield_factory.iteritems()}

    def clean_param_value(self, value):
        """Always raises :exc:`~exceptions.NotImplementedError`."""
        raise NotImplementedError("it's a result-only field")

    def clean_result_value(self, value):
        value = super(DictResultField, self).clean_result_value(value)
        if not isinstance(value, collections.Mapping):
            raise TypeError('{!r} is not a mapping'.format(value))
        keys = set(value)
        illegal_keys = keys - self.key_to_subfield.viewkeys()
        if illegal_keys:
            illegal_keys_repr = ', '.join(sorted(illegal_keys))
            raise ValueError(
                  '{!r} contains illegal keys ({!r})'.format(
                      value,
                      illegal_keys_repr))
        missing_keys = self.required_keys - keys
        if missing_keys:
            missing_keys_repr = ', '.join(sorted(missing_keys))
            raise ValueError(
                  '{!r} does not contain required keys ({!r})'.format(
                      value,
                      missing_keys_repr))
        return {
            k.decode('ascii'): self.key_to_subfield[k].clean_result_value(v)
            for k, v in value.iteritems()}


class AddressField(ResultListFieldMixin, DictResultField):

    """
    For lists of dictionaries containing ``ip`` and optionally ``cc``
    and/or ``asn``.
    """

    key_to_subfield_factory = {
        u'ip': IPv4Field,
        u'cc': CCField,
        u'asn': ASNField,
    }
    required_keys = {u'ip'}
