# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.

"""
.. note::

   For basic information how to use the classes defined in this module
   -- please consult the :ref:`data_spec_class` chapter of the tutorial.
"""


import collections

from pyramid.decorator import reify

from n6sdk.data_spec.fields import (
    Field,
    AnonymizedIPv4Field,
    ASNField,
    CCField,
    DateTimeField,
    DomainNameField,
    DomainNameSubstringField,
    EmailSimplifiedField,
    ExtendedAddressField,
    IBANSimplifiedField,
    IntegerField,
    IPv4Field,
    IPv4NetField,
    IPv6Field,
    IPv6NetField,
    ListOfDictsField,
    MD5Field,
    PortField,
    SHA1Field,
    SourceField,
    UnicodeEnumField,
    UnicodeLimitedField,
    URLField,
    URLSubstringField,
)
from n6sdk.exceptions import (
    FieldValueError,
    ParamKeyCleaningError,
    ParamValueCleaningError,
    ResultKeyCleaningError,
    ResultValueCleaningError,
    _KeyCleaningErrorMixin,
)



#
# Constants

#: A tuple of network incident data distribution restriction qualifiers
#: -- used in the :attr:`DataSpec.restriction` field specification.
RESTRICTION_ENUMS = (
    'public', 'need-to-know', 'internal',
)

#: A tuple of network incident data confidence qualifiers
#: -- used in the :attr:`DataSpec.confidence` field specification.
CONFIDENCE_ENUMS = (
    'low', 'medium', 'high',
)

#: A tuple of network incident category labels
#: -- used in the :attr:`DataSpec.category` field specification.
CATEGORY_ENUMS = (
    'amplifier',
    'bots',
    'backdoor',
    'cnc',
    'dns-query',
    'dos-attacker',
    'dos-victim',
    'flow',
    'flow-anomaly',
    'fraud',
    'leak',
    'malurl',
    'phish',
    'proxy',
    'sandbox-url',
    'scanning',
    'server-exploit',
    'spam',
    'spam-url',
    'tor',
    'vulnerable',
    'webinject',
    'other',
)

#: A tuple of network incident layer-#4-protocol labels
#: -- used in the :attr:`DataSpec.proto` field specification.
PROTO_ENUMS = (
    'tcp', 'udp', 'icmp',
)

#: A tuple of network incident origin labels
#: -- used in the :attr:`DataSpec.origin` field specification.
ORIGIN_ENUMS = (
    'c2',
    'dropzone',
    'proxy',
    'p2p-crawler',
    'p2p-drone',
    'sinkhole',
    'sandbox',
    'honeypot',
    'darknet',
    'av',
    'ids',
    'waf',
)

#: A tuple of black list item status qualifiers
#: -- used in the :attr:`DataSpec.status` field specification.
STATUS_ENUMS = (
    'active', 'delisted', 'expired', 'replaced',
)



#
# The abstract base class

class BaseDataSpec(object):

    """
    The base class for data specification classes.

    Typically, it should not be subclassed directly -- use
    :class:`DataSpec` instead.
    """

    def __init__(self, **kwargs):
        self._all_param_fields = {}
        self._required_param_fields = {}
        self._single_param_fields = {}
        self._all_result_fields = {}
        self._required_result_fields = {}

        self._set_fields()

        super(BaseDataSpec, self).__init__(**kwargs)


    #
    # public properties

    @reify
    def all_keys(self):
        """
        Instance property: a :class:`frozenset` of all keys.

        (Includes all legal parameter names and result keys.)
        """
        return self.all_param_keys | self.all_result_keys

    @reify
    def all_param_keys(self):
        """
        Instance property: a :class:`frozenset` of all legal parameter names.
        """
        return frozenset(self._all_param_fields)

    @reify
    def all_result_keys(self):
        """
        Instance property: a :class:`frozenset` of all legal result keys.
        """
        return frozenset(self._all_result_fields)


    #
    # public methods (possibly extendable)

    def clean_param_dict(self, params,
                         # optional keyword arguments:
                         ignored_keys=(),
                         forbidden_keys=(),
                         extra_required_keys=(),
                         discarded_keys=()):
        keys = self._clean_keys(
            params.viewkeys() - frozenset(ignored_keys),
            self._all_param_fields.viewkeys() - frozenset(forbidden_keys),
            self._required_param_fields.viewkeys() | frozenset(extra_required_keys),
            frozenset(discarded_keys),
            exc_class=ParamKeyCleaningError)
        return dict(self._iter_clean_param_items(params, keys))

    def clean_param_keys(self, params,
                         # optional keyword arguments:
                         ignored_keys=(),
                         forbidden_keys=(),
                         extra_required_keys=(),
                         discarded_keys=()):
        return self._clean_keys(
            params.viewkeys() - frozenset(ignored_keys),
            self._all_param_fields.viewkeys() - frozenset(forbidden_keys),
            self._required_param_fields.viewkeys() | frozenset(extra_required_keys),
            frozenset(discarded_keys),
            exc_class=ParamKeyCleaningError)

    def param_field_specs(self, which='all', multi=True, single=True):
        field_items = self._filter_by_which(which,
                                            self._all_param_fields,
                                            self._required_param_fields)
        if not multi:
            field_items &= self._single_param_fields.viewitems()
        if not single:
            field_items -= self._single_param_fields.viewitems()
        return dict(field_items)


    def clean_result_dict(self, result,
                          # optional keyword arguments:
                          ignored_keys=(),
                          forbidden_keys=(),
                          extra_required_keys=(),
                          discarded_keys=()):
        keys = self._clean_keys(
            result.viewkeys() - frozenset(ignored_keys),
            self._all_result_fields.viewkeys() - frozenset(forbidden_keys),
            self._required_result_fields.viewkeys() | frozenset(extra_required_keys),
            frozenset(discarded_keys),
            exc_class=ResultKeyCleaningError)
        return dict(self._iter_clean_result_items(result, keys))

    def clean_result_keys(self, result,
                          # optional keyword arguments:
                          ignored_keys=(),
                          forbidden_keys=(),
                          extra_required_keys=(),
                          discarded_keys=()):
        return self._clean_keys(
            result.viewkeys() - frozenset(ignored_keys),
            self._all_result_fields.viewkeys() - frozenset(forbidden_keys),
            self._required_result_fields.viewkeys() | frozenset(extra_required_keys),
            frozenset(discarded_keys),
            exc_class=ResultKeyCleaningError)

    def result_field_specs(self, which='all'):
        return dict(self._filter_by_which(which,
                                          self._all_result_fields,
                                          self._required_result_fields))


    #
    # overridable/extendable methods

    def get_adjusted_field(self, key, field, ext=None):
        if ext is not None:
            field = ext.make_extended_field(field)
        return field


    #
    # non-public internals

    def _set_fields(self):
        key_to_field = {}
        for key, field in self._iter_all_field_specs():
            key = key.decode('ascii')
            key_to_field[key] = field
            if field.in_params is not None:
                self._all_param_fields[key] = field
                if field.in_params == 'required':
                    self._required_param_fields[key] = field
                else:
                    assert field.in_params == 'optional'
                if field.single_param:
                    self._single_param_fields[key] = field
            if field.in_result is not None:
                self._all_result_fields[key] = field
                if field.in_result == 'required':
                    self._required_result_fields[key] = field
                else:
                    assert field.in_result == 'optional'
        # making all fields (including those Ext-updated)
        # accessible also as instance attributes
        vars(self).update(key_to_field)

    def _iter_all_field_specs(self):
        key_to_ext = collections.defaultdict(Ext)
        seen_keys = set()
        attr_containers = (self,) + self.__class__.__mro__
        for ac in attr_containers:
            for key, obj in vars(ac).iteritems():
                if isinstance(obj, Ext):
                    key_to_ext[key].nondestructive_update(obj)
                    continue
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                if isinstance(obj, Field):
                    field_ext = key_to_ext.get(key)
                    field = self.get_adjusted_field(key, obj, field_ext)
                    yield key, field
                    for extra in self._iter_extra_param_specs(key, field):
                        yield extra

    def _iter_extra_param_specs(self, key, parent_field):
        for key_suffix, xfield in parent_field.extra_params.iteritems():
            if xfield is None:
                # field was masked ("removed") using Ext, e.g. in a subclass
                continue
            if not isinstance(xfield, Field):
                raise TypeError('{!r} is not a {!r} instance'
                                .format(xfield, Field))
            xkey = '{}.{}'.format(key, key_suffix)
            xfield = self.get_adjusted_field(xkey, xfield)
            yield xkey, xfield
            # recursive yielding:
            for extra in self._iter_extra_param_specs(xkey, xfield):
                yield extra

    @staticmethod
    def _clean_keys(keys, legal_keys, required_keys, discarded_keys,
                    exc_class):
        illegal_keys = keys - legal_keys
        missing_keys = required_keys - keys
        if illegal_keys or missing_keys:
            assert issubclass(exc_class, _KeyCleaningErrorMixin)
            raise exc_class(illegal_keys, missing_keys)
        return {key.decode('ascii') for key in (keys - discarded_keys)}

    def _iter_clean_param_items(self, params, keys):
        error_info_seq = []
        for key in keys:
            assert key in self._all_param_fields
            assert key in params
            field = self._all_param_fields[key]
            param_values = params[key]
            assert param_values and type(param_values) is list
            assert hasattr(field, 'single_param')
            if field.single_param and len(param_values) > 1:
                error_info_seq.append((
                    key,
                    param_values,
                    FieldValueError(public_message=(
                        u'Multiple values for a single-value-only field.'))
                ))
            else:
                cleaned_values = []
                for value in param_values:
                    try:
                        cleaned_val = field.clean_param_value(value)
                    except Exception as exc:
                        error_info_seq.append((key, value, exc))
                    else:
                        cleaned_values.append(cleaned_val)
                if cleaned_values:
                    yield key, cleaned_values
        if error_info_seq:
            raise ParamValueCleaningError(error_info_seq)

    def _iter_clean_result_items(self, result, keys):
        error_info_seq = []
        for key in keys:
            assert key in self._all_result_fields
            assert key in result
            field = self._all_result_fields[key]
            value = result[key]
            try:
                yield key, field.clean_result_value(value)
            except Exception as exc:
                error_info_seq.append((key, value, exc))
        if error_info_seq:
            raise ResultValueCleaningError(error_info_seq)

    @staticmethod
    def _filter_by_which(which, all_fields, required_fields):
        # select fields that match the `which` argument
        if which == 'all':
            return all_fields.viewitems()
        elif which == 'required':
            return required_fields.viewitems()
        elif which == 'optional':
            return all_fields.viewitems() - required_fields.viewitems()
        else:
            raise ValueError("{!r} is not one of: 'all', 'required', 'optional'"
                             .format(which))



#
# The concrete base class

class DataSpec(BaseDataSpec):

    """
    The basic, ready-to-use, data specification class.

    You can use it directly or inherit from it.
    """

    #
    # Identification, categorization and other event metadata

    id = UnicodeLimitedField(
        in_params='optional',
        in_result='required',
        max_length=64,
    )

    source = SourceField(
        in_params='optional',
        in_result='required',
    )

    restriction = UnicodeEnumField(
        in_params='optional',
        in_result='required',
        enum_values=RESTRICTION_ENUMS,
    )

    confidence = UnicodeEnumField(
        in_params='optional',
        in_result='required',
        enum_values=CONFIDENCE_ENUMS,
    )

    category = UnicodeEnumField(
        in_params='optional',
        in_result='required',
        enum_values=CATEGORY_ENUMS,
    )

    time = DateTimeField(
        in_params=None,
        in_result='required',

        extra_params=dict(
            min=DateTimeField(          # `time.min`
                in_params='optional',
                single_param=True,
            ),
            max=DateTimeField(          # `time.max`
                in_params='optional',
                single_param=True,
            ),
            until=DateTimeField(        # `time.until`
                in_params='optional',
                single_param=True,
            ),
        ),
    )

    modified = DateTimeField(
        in_params=None,
        in_result='optional',

        extra_params=dict(
            min=DateTimeField(          # `modified.min`
                in_params='optional',
                single_param=True,
            ),
            max=DateTimeField(          # `modified.max`
                in_params='optional',
                single_param=True,
            ),
            until=DateTimeField(        # `modified.until`
                in_params='optional',
                single_param=True,
            ),
        ),
    )

    origin = UnicodeEnumField(
        in_params='optional',
        in_result='optional',
        enum_values=ORIGIN_ENUMS,
    )

    name = UnicodeLimitedField(
        in_params='optional',
        in_result='optional',
        max_length=255,
    )

    target = UnicodeLimitedField(
        in_params='optional',
        in_result='optional',
        max_length=100,
    )

    #
    # An `address` is a list of dicts -- each containing either
    # `ip` or `ipv6` (but not both) and optionally some or all of:
    # `asn`, `cc`, `dir`, `rdns`

    address = ExtendedAddressField(
        in_params=None,
        in_result='optional',
    )

    #
    # Query params related to the components of `address` items

    ip = IPv4Field(
        in_params='optional',
        in_result=None,

        extra_params=dict(
            net=IPv4NetField(           # `ip.net`
                in_params='optional',
            ),
        ),
    )

    ipv6 = IPv6Field(
        in_params='optional',
        in_result=None,

        extra_params=dict(
            net=IPv6NetField(           # `ipv6.net`
                in_params='optional',
            ),
        ),
    )

    asn = ASNField(
        in_params='optional',
        in_result=None,
    )

    cc = CCField(
        in_params='optional',
        in_result=None,
    )

    #
    # Other "technical" event properties

    url = URLField(
        in_params='optional',
        in_result='optional',

        extra_params=dict(
            sub=URLSubstringField(      # `url.sub`
                in_params='optional',
            ),
        ),
    )

    fqdn = DomainNameField(
        in_params='optional',
        in_result='optional',

        extra_params=dict(
            sub=DomainNameSubstringField(   # `fqdn.sub`
                in_params='optional',
            ),
        ),
    )

    proto = UnicodeEnumField(
        in_params='optional',
        in_result='optional',
        enum_values=PROTO_ENUMS,
    )

    sport = PortField(
        in_params='optional',
        in_result='optional',
    )

    dport = PortField(
        in_params='optional',
        in_result='optional',
    )

    dip = IPv4Field(
        in_params='optional',
        in_result='optional',
    )

    adip = AnonymizedIPv4Field(
        in_params=None,
        in_result='optional',
    )

    md5 = MD5Field(
        in_params='optional',
        in_result='optional',
    )

    sha1 = SHA1Field(
        in_params='optional',
        in_result='optional',
    )

    injects = ListOfDictsField(
        in_params=None,
        in_result='optional',
    )

    registrar = UnicodeLimitedField(
        in_params='optional',
        in_result='optional',
        max_length=100,
    )

    url_pattern = UnicodeLimitedField(
        in_params='optional',
        in_result='optional',
        max_length=255,
    )

    username = UnicodeLimitedField(
        in_params='optional',
        in_result='optional',
        max_length=64,
    )

    x509fp_sha1 = SHA1Field(
        in_params='optional',
        in_result='optional',
    )

    #
    # Others...

    email = EmailSimplifiedField(
        in_params='optional',
        in_result='optional',
    )

    iban = IBANSimplifiedField(
        in_params='optional',
        in_result='optional',
    )

    phone = UnicodeLimitedField(
        in_params='optional',
        in_result='optional',
        max_length=20,
    )

    expires = DateTimeField(
        in_params=None,
        in_result='optional',
    )

    active = Field(
        in_params=None,
        in_result=None,

        extra_params=dict(
            min=DateTimeField(          # `active.min`
                in_params='optional',
                single_param=True,
            ),
            max=DateTimeField(          # `active.max`
                in_params='optional',
                single_param=True,
            ),
            until=DateTimeField(        # `active.until`
                in_params='optional',
                single_param=True,
            ),
        ),
    )

    status = UnicodeEnumField(
        in_params='optional',
        in_result='optional',
        enum_values=STATUS_ENUMS,
    )

    replaces = UnicodeLimitedField(
        in_params='optional',
        in_result='optional',
        max_length=64,
    )

    until = DateTimeField(
        in_params=None,
        in_result='optional',
    )

    count = IntegerField(
        in_params=None,
        in_result='optional',
        min_value=0,
        max_value=(2 ** 15 - 1),
    )



#
# Auxiliary classes

class Ext(dict):

    """
    A :class:`dict`-like class for extending field properties in
    :class:`DataSpec` subclasses.
    """

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                               super(Ext, self).__repr__())

    def copy(self):
        return self.__class__(self)

    def make_extended_field(self, field):
        merged_init_kwargs = self.copy()
        merged_init_kwargs.nondestructive_update(field._init_kwargs)
        return field.__class__(**merged_init_kwargs)

    def nondestructive_update(self, other):
        if isinstance(other, collections.Mapping):
            other = other.iteritems()
        for key, value in other:
            stored_value = self.setdefault(key, value)
            if (stored_value is not value) and isinstance(stored_value, Ext):
                if isinstance(value, Field):
                    self[key] = stored_value.make_extended_field(value)
                elif isinstance(value, collections.Mapping):
                    merged_value = stored_value.copy()
                    merged_value.nondestructive_update(value)
                    self[key] = merged_value
