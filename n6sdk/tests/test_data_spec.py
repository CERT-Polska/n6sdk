# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.


import collections
import datetime
import unittest

from mock import ANY

from n6sdk.data_spec import (
    DataSpec,
    Ext,
)
from n6sdk.data_spec.fields import (
    AddressField,
    AnonymizedIPv4Field,
    ASNField,
    CCField,
    DateTimeField,
    DomainNameField,
    DomainNameSubstringField,
    IntegerField,
    IPv4Field,
    IPv4NetField,
    MD5Field,
    PortField,
    SHA1Field,
    SourceField,
    UnicodeField,
    UnicodeEnumField,
    UnicodeLimitedField,
    URLField,
    URLSubstringField,
)
from n6sdk.datetime_helpers import (
    FixedOffsetTimezone,
)
from n6sdk.exceptions import (
    ParamKeyCleaningError,
    ParamValueCleaningError,
    ResultKeyCleaningError,
    ResultValueCleaningError
)



#
# Mix-ins for test case classes
#

class GenericDataSpecTestMixin(object):

    def assertEqualIncludingTypes(self, first, second, msg=None):
        self.assertEqual(first, second)
        self.assertIs(type(first), type(second),
                      'type of {!r} ({}) is not type of {!r} ({})'
                      .format(first, type(first), second, type(second)))
        if (isinstance(first, (collections.Sequence, collections.Set)) and
              not isinstance(first, basestring)):
            for val1, val2 in zip(sorted(first), sorted(second)):
                self.assertEqualIncludingTypes(val1, val2)
        elif isinstance(first, collections.Mapping):
            for key1, key2 in zip(sorted(first.iterkeys()),
                                  sorted(second.iterkeys())):
                self.assertEqualIncludingTypes(key1, key2)
            for key in first:
                self.assertEqualIncludingTypes(first[key], second[key])



class MixinBase(GenericDataSpecTestMixin):

    DEL = object()  # a 'do-not-include-me' sentinel value used here and there

    data_spec_class = DataSpec

    key_to_field_type = {
        u'id': UnicodeLimitedField,
        u'source': SourceField,
        u'restriction': UnicodeEnumField,
        u'confidence': UnicodeEnumField,
        u'category': UnicodeEnumField,
        u'time': DateTimeField,
        u'time.min': DateTimeField,
        u'time.max': DateTimeField,
        u'origin': UnicodeEnumField,
        u'name': UnicodeLimitedField,
        u'target': UnicodeLimitedField,
        u'address': AddressField,
        u'ip': IPv4Field,
        u'ip.net': IPv4NetField,
        u'asn': ASNField,
        u'cc': CCField,
        u'url': URLField,
        u'url.sub': URLSubstringField,
        u'fqdn': DomainNameField,
        u'fqdn.sub': DomainNameSubstringField,
        u'proto': UnicodeEnumField,
        u'sport': PortField,
        u'dport': PortField,
        u'dip': IPv4Field,
        u'adip': AnonymizedIPv4Field,
        u'md5': MD5Field,
        u'sha1': SHA1Field,
        u'expires': DateTimeField,
        u'active.min': DateTimeField,
        u'active.max': DateTimeField,
        u'status': UnicodeEnumField,
        u'replaces': UnicodeLimitedField,
        u'until': DateTimeField,
        u'count': IntegerField,
    }

    def setUp(self):
        self.ds = self.data_spec_class()
        self._selftest_assertions()

    def _selftest_assertions(self):
        assert self.keys <= set(self.key_to_field_type)
        assert self.required_keys <= self.keys
        assert self.required_keys <= set(self.example_given_dict)
        assert set(self.example_given_dict) <= self.keys
        assert (set(self.example_given_dict) ==
                set(self.example_cleaned_dict))

    @property
    def optional_keys(self):
        return self.keys - self.required_keys

    def _given_dict(self, **kwargs):
        d = dict(self.example_given_dict, **kwargs)
        return {k: v for k, v in d.iteritems()
                if v is not self.DEL}

    def _cleaned_dict(self, **kwargs):
        d = dict(self.example_cleaned_dict, **kwargs)
        return {k: v for k, v in d.iteritems()
                if v is not self.DEL}

    def _test_illegal_keys(self, clean_method):
        given_dict = self._given_dict(
            **dict.fromkeys(self.example_illegal_keys))
        with self.assertRaises(self.key_cleaning_error) as cm:
            clean_method(given_dict)
        exc = cm.exception
        self.assertEqual(exc.illegal_keys, self.example_illegal_keys)
        self.assertEqual(exc.missing_keys, set())

    def _test_missing_keys(self, clean_method):
        if not self.example_missing_keys:
            assert not self.required_keys
            return
        given_dict = self._given_dict(
            **dict.fromkeys(self.example_missing_keys, self.DEL))
        with self.assertRaises(self.key_cleaning_error) as cm:
            clean_method(given_dict)
        exc = cm.exception
        self.assertEqual(exc.illegal_keys, set())
        self.assertEqual(exc.missing_keys, self.example_missing_keys)

    def _test_field_specs(self, field_specs, expected_keys):
        self.assertIsInstance(field_specs, dict)
        self.assertEqualIncludingTypes(
            sorted(field_specs),
            sorted(expected_keys))
        for key, field in field_specs.iteritems():
            self.assertIsInstance(field, self.key_to_field_type[key])


class ParamCleanMixin(MixinBase):

    # param-fields-related

    key_cleaning_error = ParamKeyCleaningError

    keys = {
        u'id', u'source', u'restriction', u'confidence', u'category',
        u'time.min', u'time.max',
        u'origin', u'name', u'target',
        u'ip', u'ip.net', u'asn', u'cc',
        u'url', u'url.sub', u'fqdn', u'fqdn.sub',
        u'proto', u'sport', u'dport', u'dip',
        u'md5', u'sha1',
        u'active.min', u'active.max',
        u'status', u'replaces',
    }

    required_keys = set()

    single_param_keys = {
        u'time.min', u'time.max',
        u'active.min', u'active.max',
    }

    example_given_dict = {
        'id': 'aaaaa,bbb',
        u'category': u'bots',
        'source': 'some.source,some.otherrrrrrrrrrrrrrrrrrrrrrr',
        u'confidence': u'high,medium',
        'ip': '100.101.102.103',
        u'cc': 'PL,US',
        'dip': u'0.10.20.30',
        u'asn': '80000,1',
        'dport': u'1234',
        u'ip.net': u'100.101.102.103/32,1.2.3.4/7',
        'time.min': '2014-04-01 01:07:42+02:00',
        u'active.min': u'2015-05-02T24:00',
        'url': 'http://www.ołówek.EXAMPLĘ.com/\xdd-TRALALą.html',
        u'fqdn': u'www.test.org,www.ołówek.EXAMPLĘ.com',
        'url.sub': ('xx' + 682 * '\xcc'),
        u'fqdn.sub': 'ołówek',
    }

    example_cleaned_dict = {
        # (keys converted to unicode, using the ASCII encoding;
        # values transformed into 1-or-many-element-lists)

        # (str converted to unicode)
        u'id': [u'aaaaa', u'bbb'],
        u'category': [u'bots'],
        u'source': [u'some.source', u'some.otherrrrrrrrrrrrrrrrrrrrrrr'],
        u'confidence': [u'high', u'medium'],
        u'ip': [u'100.101.102.103'],
        u'cc': [u'PL', u'US'],
        u'dip': [u'0.10.20.30'],

        # (numbers converted to int)
        u'asn': [80000, 1],
        u'dport': [1234],

        # (IP network specs converted to (ipv4, number) pairs)
        u'ip.net': [(u'100.101.102.103', 32), (u'1.2.3.4', 7)],

        # (a TZ +02:00 datetime converted to UTC)
        u'time.min': [datetime.datetime(2014, 3, 31, 23, 7, 42)],

        # (24:00 on 2nd of May converted to 00:00 on 3rd of May)
        u'active.min': [datetime.datetime(2015, 05, 03)],

        # (non-UTF-8 URL characters surrogate-escaped)
        u'url': [u'http://www.ołówek.EXAMPLĘ.com/\udcdd-TRALALą.html'],
        u'url.sub': [u'xx' + 682 * u'\udccc'],

        # (domain name IDNA-encoded)
        u'fqdn': [u'www.test.org', u'www.xn--owek-qqa78b.xn--exampl-14a.com'],
        u'fqdn.sub': [u'xn--owek-qqa78b'],
    }

    example_illegal_keys = {
        u'foo',
        u'illegal',
        u'address',  # 'address' is a result-only field
    }

    example_missing_keys = set()

    def _selftest_assertions(self):
        super(ParamCleanMixin, self)._selftest_assertions()
        assert self.single_param_keys <= self.keys


class ResultCleanMixin(MixinBase):

    # result-fields-related

    key_cleaning_error = ResultKeyCleaningError

    keys = {
        u'id', u'source', u'restriction', u'confidence', u'category', u'time',
        u'origin', u'name', u'target',
        u'address', u'url', u'fqdn',
        u'proto', u'sport', u'dport', u'dip', u'adip',
        u'md5', u'sha1',
        u'expires', u'status', u'replaces', u'until', u'count',
    }

    required_keys = {
        u'id', u'source', u'restriction', u'confidence', u'category', u'time',
    }

    example_given_dict = {
        'id': 'aaaaa',
        'source': 'some.source-eeeeeeeeeeeeeeeeeeee',
        u'restriction': 'public',
        'confidence': u'low',
        u'category': u'bots',
        'adip': u'x.10.20.30',
        'address': [
            {
                'ip': u'100.101.102.103',
                u'cc': u'PL',
                'asn': 80000,
            },
            {
                u'ip': '10.0.255.128',
                'cc': u'US',
                u'asn': 10000L,  # long
            },
        ],
        'dport': 1234L,  # long
        u'time': datetime.datetime(
            2014, 4, 1, 1, 7, 42,              # a TZ-aware datetime
            tzinfo=FixedOffsetTimezone(120)),  # (timezone UTC+02:00)
        'url': 'http://www.ołówek.EXAMPLĘ.com/\xdd-TRALALą.html',
        u'fqdn': u'www.ołówek.EXAMPLĘ.com',
    }

    example_cleaned_dict = {
        # (keys converted to unicode, using the ASCII encoding)

        # (str values converted to unicode)
        u'id': u'aaaaa',
        u'source': u'some.source-eeeeeeeeeeeeeeeeeeee',
        u'restriction': u'public',
        u'confidence': u'low',
        u'category': u'bots',
        u'adip': u'x.10.20.30',

        u'address': [
            {
                u'ip': u'100.101.102.103',
                u'cc': u'PL',
                u'asn': 80000,  # int
            },
            {
                u'ip': u'10.0.255.128',
                u'cc': u'US',
                u'asn': 10000,  # int
            },
        ],
        u'dport': 1234,  # int

        # (a TZ +02:00 datetime converted to UTC)
        u'time': datetime.datetime(2014, 3, 31, 23, 7, 42),

        # (non-UTF-8 URL characters surrogate-escaped)
        u'url': u'http://www.ołówek.EXAMPLĘ.com/\udcdd-TRALALą.html',

        # (domain name IDNA-encoded)
        u'fqdn': u'www.xn--owek-qqa78b.xn--exampl-14a.com',
    }

    example_illegal_keys = {
        'foo',
        u'illegal',
        'ip',
    }

    example_missing_keys = {
        u'id',
        'restriction',
    }


#
# Similar mix-ins for tests of a DataSpec subclass
# (with extended/removed/replaced/added fields)

class SubclassMixinBase(MixinBase):

    class data_spec_class(DataSpec):
        id = Ext(                        # extended
            in_params='required',
            # (note: `in_result` left as 'required')
            max_length=3,
        )
        category = None                  # removed (masked)
        dport = IntegerField(            # replaced
            in_params='optional',
            in_result=None,
            min_value=10000,
            max_value=65535,
        )
        justnew = UnicodeField(          # added
            in_params='optional',
            in_result='required',
        )
        notused = UnicodeField()     # not used because not tagged as
                                     # `in_params` and/or `in_results`

        url = Ext(                       # extended
            extra_params=Ext(            #  extended
                sub=Ext(                 #   extended
                    max_length=100,
                    checking_bytes_length=False,
                    in_params='required',
                    # (note: `in_result` left as None)
                )
            ),
            in_params=None,
            # (note: `in_result` left as 'optional')
            custom_info=dict(
                tralala=dict(ham='spam'),
            ),
        )
        active = Ext(                    # extended
            extra_params=Ext(            #  extended
                min=IntegerField(        #   replaced
                    in_params='optional',
                    # (note: `in_result` left as None)
                ),
                max=None,                #   removed (masked)
            )
        )
        fqdn = Ext(                      # extended
            extra_params={},             #  replaced (removing 'fqdn.sub')
            in_result='required',
            # (note: `in_params` left as 'optional')
        )

    # adjusting test class attributes to match the above data spec subclass
    key_to_field_type = MixinBase.key_to_field_type.copy()
    del key_to_field_type[u'category']
    del key_to_field_type[u'active.max']
    del key_to_field_type[u'fqdn.sub']
    key_to_field_type.update({
        u'dport': IntegerField,
        u'active.min': IntegerField,
        u'justnew': UnicodeField,
    })


class SubclassParamCleanMixin(SubclassMixinBase, ParamCleanMixin):

    # param-fields-related

    keys = ParamCleanMixin.keys.copy()
    keys -= {u'category', u'url', u'fqdn.sub', u'active.max'}
    keys |= {u'justnew'}

    required_keys = {u'id', u'url.sub'}

    single_param_keys = ParamCleanMixin.single_param_keys.copy()
    single_param_keys -= {u'active.min', u'active.max'}

    example_given_dict = ParamCleanMixin.example_given_dict.copy()
    del example_given_dict[u'category']
    del example_given_dict[u'url']
    del example_given_dict[u'fqdn.sub']
    example_given_dict.update({
        'id': 'aaa,bbb',
        u'dport': '12345',
        'active.min': '9876543210,-123',
        u'url.sub': 100 * '\xcc',
        'justnew': u'xyz,123',
    })

    example_cleaned_dict = ParamCleanMixin.example_cleaned_dict.copy()
    del example_cleaned_dict['category']
    del example_cleaned_dict['url']
    del example_cleaned_dict['fqdn.sub']
    example_cleaned_dict.update({
        u'id': [u'aaa', u'bbb'],
        u'dport': [12345],
        u'active.min': [9876543210, -123],
        u'url.sub': [100 * u'\udccc'],
        u'justnew': [u'xyz', u'123'],
    })

    example_illegal_keys = {
        'foo',
        u'illegal',
        'category',
        u'active.max',
        'url',
        u'fqdn.sub',
        'notused',
        u'address',
    }

    example_missing_keys = {
        'id',
        u'url.sub',
    }


class SubclassResultCleanMixin(SubclassMixinBase, ResultCleanMixin):

    # result-fields-related

    keys = ResultCleanMixin.keys.copy()
    keys -= {u'category', u'dport'}
    keys |= {u'justnew'}

    required_keys = ResultCleanMixin.required_keys.copy()
    required_keys -= {u'category'}
    required_keys |= {u'justnew', u'fqdn'}

    example_given_dict = ResultCleanMixin.example_given_dict.copy()
    del example_given_dict[u'category']
    del example_given_dict[u'dport']
    example_given_dict.update({
        'id': 'aaa',
        u'justnew': 'xyzxyz',
    })

    example_cleaned_dict = ResultCleanMixin.example_cleaned_dict.copy()
    del example_cleaned_dict['category']
    del example_cleaned_dict['dport']
    example_cleaned_dict.update({
        u'id': u'aaa',
        u'justnew': u'xyzxyz',
    })

    example_illegal_keys = {
        u'foo',
        'illegal',
        u'category',
        'dport',
        u'notused',
        'ip',
    }

    example_missing_keys = {
        u'id',
        'restriction',
        u'justnew',
        'fqdn',
    }



#
# Concrete test cases
#

#
# Param-fields-related:

class TestDataSpec_clean_param_dict(ParamCleanMixin, unittest.TestCase):

    def test_valid(self):
        given_dict = self._given_dict()
        cleaned = self.ds.clean_param_dict(given_dict)
        expected_cleaned = self._cleaned_dict()
        self.assertEqualIncludingTypes(cleaned, expected_cleaned)

    def test_valid_ignoring_some_keys(self):
        given_dict = self._given_dict(ip='badvalue', illegal='spam')
        cleaned = self.ds.clean_param_dict(
            given_dict,
            ignored_keys=['ip', 'illegal'])
        expected_cleaned = self._cleaned_dict(ip=self.DEL)
        self.assertEqualIncludingTypes(cleaned, expected_cleaned)

    def test_illegal_keys(self):
        self._test_illegal_keys(self.ds.clean_param_dict)

    def test_missing_keys(self):
        self._test_missing_keys(self.ds.clean_param_dict)

    def test_non_string_param(self):
        given_dict = self._given_dict(dport=1234)
        with self.assertRaises(TypeError):
            self.ds.clean_param_dict(given_dict)

    def test_invalid_value__source_too_long(self):
        given_dict = self._given_dict(
            source='some.source,some.otherrrrrrrrrrrrrrrrrrrrrrr' + 'x')
        with self.assertRaises(ParamValueCleaningError) as cm:
            self.ds.clean_param_dict(given_dict)
        exc = cm.exception
        self.assertEqual(exc.error_info_seq, [
            ('source', 'some.source,some.otherrrrrrrrrrrrrrrrrrrrrrrx', ANY),
        ])
        self.assertIsInstance(exc.error_info_seq[0][2], Exception)

    def test_several_invalid_values(self):
        given_dict = self._given_dict(**{
            # not in enum set
            'confidence': u'high,medium,INVALID',
            # invalid IPv4 (333 > 255)
            'ip': '333.101.102.103',
            # invalid CIDR IPv4 network spec (33 > 32, 333 > 255)
            'ip.net': u'100.101.102.103/33,333.2.3.4/1',
            # invalid country code ('!' not allowed)
            'cc': '!!,US',
            # IP starts with an anonymized octet
            'dip': u'x.20.30.40',
            # too big number
            'asn': '4294967297',
            # too small number
            'dport': u'-1234',
            # invalid time
            'time.min': '2014-04-01 61:61:61+02:00',
            # invalid date
            'active.max': u'2015-05-99T15:25',
            # too long URL
            'url': (2049 * 'x'),
            # too long URL substring
            'url.sub': (2049 * 'x'),
            # too long label in a domain name
            'fqdn': u'www.test.org,www.ołówekkkkkkkkkkkkkkkkkkkkkkkkkkk'
                    u'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk'
                    u'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.EXAMPLĘ.com',
        })
        with self.assertRaises(ParamValueCleaningError) as cm:
            self.ds.clean_param_dict(given_dict)
        exc = cm.exception
        self.assertEqual(sorted(exc.error_info_seq), sorted([
            ('confidence', u'high,medium,INVALID', ANY),
            ('ip', '333.101.102.103', ANY),
            ('ip.net', u'100.101.102.103/33,333.2.3.4/1', ANY),
            ('cc', '!!,US', ANY),
            ('dip', ANY, ANY),
            ('asn', ANY, ANY),
            ('dport', ANY, ANY),
            ('time.min', ANY, ANY),
            ('active.max', ANY, ANY),
            ('url', ANY, ANY),
            ('url.sub', ANY, ANY),
            ('fqdn', ANY, ANY),
        ]))
        self.assertTrue(all(
            isinstance(info[1], basestring) and isinstance(info[2], Exception)
            for info in exc.error_info_seq))


class TestDataSpec_clean_param_keys(ParamCleanMixin, unittest.TestCase):

    def test_valid(self):
        given_dict = self._given_dict()
        cleaned_keys = self.ds.clean_param_keys(given_dict)
        expected_cleaned_keys = set(self._cleaned_dict())
        self.assertEqualIncludingTypes(cleaned_keys, expected_cleaned_keys)

    def test_valid_ignoring_some_keys(self):
        given_dict = self._given_dict(ip='badvalue', illegal='spam')
        cleaned_keys = self.ds.clean_param_keys(
            given_dict,
            ignored_keys=['ip', 'illegal'])
        expected_cleaned_keys = set(self._cleaned_dict(ip=self.DEL))
        self.assertEqualIncludingTypes(cleaned_keys, expected_cleaned_keys)

    def test_illegal_keys(self):
        self._test_illegal_keys(self.ds.clean_param_keys)

    def test_missing_keys(self):
        self._test_missing_keys(self.ds.clean_param_keys)


class TestDataSpec_param_field_specs(ParamCleanMixin, unittest.TestCase):

    def test_all(self):
        field_specs = self.ds.param_field_specs()
        self._test_field_specs(
            field_specs,
            expected_keys=self.keys)

    def test_all_without_multi(self):
        field_specs = self.ds.param_field_specs(multi=False)
        self._test_field_specs(
            field_specs,
            expected_keys=self.single_param_keys)

    def test_all_without_single(self):
        field_specs = self.ds.param_field_specs(single=False)
        self._test_field_specs(
            field_specs,
            expected_keys=(self.keys - self.single_param_keys))

    def test_all_without_multi_and_without_single(self):
        field_specs = self.ds.param_field_specs(multi=False, single=False)
        # always must be empty
        self._test_field_specs(
            field_specs,
            expected_keys=set())

    def test_required(self):
        field_specs = self.ds.param_field_specs('required')
        self._test_field_specs(
            field_specs,
            expected_keys=self.required_keys)

    def test_required_without_multi(self):
        field_specs = self.ds.param_field_specs('required', multi=False)
        self._test_field_specs(
            field_specs,
            expected_keys=(self.required_keys & self.single_param_keys))

    def test_required_without_single(self):
        field_specs = self.ds.param_field_specs('required', single=False)
        self._test_field_specs(
            field_specs,
            expected_keys=(self.required_keys - self.single_param_keys))

    def test_required_without_multi_and_without_single(self):
        field_specs = self.ds.param_field_specs(
            'required', multi=False, single=False)
        # always must be empty
        self._test_field_specs(
            field_specs,
            expected_keys=set())

    def test_optional(self):
        field_specs = self.ds.param_field_specs('optional')
        self._test_field_specs(
            field_specs,
            expected_keys=self.optional_keys)

    def test_optional_without_multi(self):
        field_specs = self.ds.param_field_specs('optional', multi=False)
        self._test_field_specs(
            field_specs,
            expected_keys=(self.optional_keys & self.single_param_keys))

    def test_optional_without_single(self):
        field_specs = self.ds.param_field_specs('optional', single=False)
        self._test_field_specs(
            field_specs,
            expected_keys=(self.optional_keys - self.single_param_keys))

    def test_optional_without_multi_and_without_single(self):
        field_specs = self.ds.param_field_specs(
            'optional', multi=False, single=False)
        # always must be empty
        self._test_field_specs(
            field_specs,
            expected_keys=set())


class TestDataSpecSubclass_clean_param_dict(SubclassParamCleanMixin,
                                            TestDataSpec_clean_param_dict):
    """Like TestDataSpec_clean_param_dict but for a DataSpec subclass."""

    def test_several_invalid_values(self):
        given_dict = self._given_dict(**{
            'id': 'aaaaa,bbb',         # 'aaaaa' it is too long
            'confidence': u'high,medium,INVALID',
            'justnew': 'xyz\xdd,123',  # non-UTF-8 value
            'dport': u'1234',          # the number is too low
            'url.sub': (101 * 'x'),    # too long
        })
        with self.assertRaises(ParamValueCleaningError) as cm:
            self.ds.clean_param_dict(given_dict)
        exc = cm.exception
        self.assertEqual(sorted(exc.error_info_seq), sorted([
            ('id', 'aaaaa,bbb', ANY),
            ('confidence', u'high,medium,INVALID', ANY),
            ('justnew', 'xyz\xdd,123', ANY),
            ('dport', u'1234', ANY),
            ('url.sub', (101 * 'x'), ANY),
        ]))
        self.assertTrue(all(
            isinstance(info[1], basestring) and isinstance(info[2], Exception)
            for info in exc.error_info_seq))


class TestDataSpecSubclass_clean_param_keys(SubclassParamCleanMixin,
                                            TestDataSpec_clean_param_keys):
    """Like TestDataSpec_clean_param_keys but for a DataSpec subclass."""


class TestDataSpecSubclass_param_field_specs(SubclassParamCleanMixin,
                                             TestDataSpec_param_field_specs):
    """Like TestDataSpec_param_field_specs but for a DataSpec subclass."""


#
# Result-fields-related:

class TestDataSpec_clean_result_dict(ResultCleanMixin, unittest.TestCase):

    def test_valid(self):
        given_dict = self._given_dict()
        cleaned = self.ds.clean_result_dict(given_dict)
        expected_cleaned = self._cleaned_dict()
        self.assertEqualIncludingTypes(cleaned, expected_cleaned)

    def test_valid_ignoring_some_keys(self):
        given_dict = self._given_dict(address='badvalue', illegal='spam')
        cleaned = self.ds.clean_result_dict(
            given_dict,
            ignored_keys=['address', 'illegal'])
        expected_cleaned = self._cleaned_dict(address=self.DEL)
        self.assertEqualIncludingTypes(cleaned, expected_cleaned)

    def test_illegal_keys(self):
        self._test_illegal_keys(self.ds.clean_result_dict)

    def test_missing_keys(self):
        self._test_missing_keys(self.ds.clean_result_dict)

    def test_invalid_value__source_too_long(self):
        given_dict = self._given_dict(
            source='some.otherrrrrrrrrrrrrrrrrrrrrrr' + 'x')
        with self.assertRaises(ResultValueCleaningError) as cm:
            self.ds.clean_result_dict(given_dict)
        exc = cm.exception
        self.assertEqual(exc.error_info_seq, [
            ('source', 'some.otherrrrrrrrrrrrrrrrrrrrrrrx', ANY),
        ])
        self.assertIsInstance(exc.error_info_seq[0][2], Exception)

    def test_several_invalid_values(self):
        given_dict = self._given_dict(**{
            # not in enum set
            'confidence': u'INVALID',
            'address': [
                {
                    # invalid IPv4 (333 > 255)
                    'ip': '333.101.102.103',
                }
            ],
            # IP does not stard with an anonymized octet
            'adip': u'10.20.30.40',
            # too big number
            'dport': 65536,
            # not a valid date + time specification
            'time': '2014-04-01 25:30:22',
            # too long URL
            'url': (2049 * 'x'),
            # too long label in a domain name
            'fqdn': u'www.test.org,www.ołówekkkkkkkkkkkkkkkkkkkkkkkkkkk'
                    u'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk'
                    u'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.EXAMPLĘ.com',
            # not an MD5 hex-digest
            'md5': 'aaa',
        })
        with self.assertRaises(ResultValueCleaningError) as cm:
            self.ds.clean_result_dict(given_dict)
        exc = cm.exception
        self.assertEqual(sorted(exc.error_info_seq), sorted([
            ('confidence', u'INVALID', ANY),
            ('address', [{'ip': '333.101.102.103'}], ANY),
            ('adip', ANY, ANY),
            ('dport', ANY, ANY),
            ('time', ANY, ANY),
            ('url', ANY, ANY),
            ('fqdn', ANY, ANY),
            ('md5', ANY, ANY),
        ]))
        self.assertTrue(all(isinstance(info[2], Exception)
                            for info in exc.error_info_seq))


class TestDataSpec_clean_result_keys(ResultCleanMixin, unittest.TestCase):

    def test_valid(self):
        given_dict = self._given_dict()
        cleaned_keys = self.ds.clean_result_keys(given_dict)
        expected_cleaned_keys = set(self._cleaned_dict())
        self.assertEqualIncludingTypes(cleaned_keys, expected_cleaned_keys)

    def test_valid_ignoring_some_keys(self):
        given_dict = self._given_dict(address='badvalue', illegal='spam')
        cleaned_keys = self.ds.clean_result_keys(
            given_dict,
            ignored_keys=['address', 'illegal'])
        expected_cleaned_keys = set(self._cleaned_dict(address=self.DEL))
        self.assertEqualIncludingTypes(cleaned_keys, expected_cleaned_keys)

    def test_illegal_keys(self):
        self._test_illegal_keys(self.ds.clean_result_keys)

    def test_missing_keys(self):
        self._test_missing_keys(self.ds.clean_result_keys)


class TestDataSpec_result_field_specs(ResultCleanMixin, unittest.TestCase):

    def test_all(self):
        field_specs = self.ds.result_field_specs()
        self._test_field_specs(
            field_specs,
            expected_keys=self.keys)

    def test_required(self):
        field_specs = self.ds.result_field_specs('required')
        self._test_field_specs(
            field_specs,
            expected_keys=self.required_keys)

    def test_optional(self):
        field_specs = self.ds.result_field_specs('optional')
        self._test_field_specs(
            field_specs,
            expected_keys=(self.optional_keys))


class TestDataSpecSubclass_clean_result_dict(SubclassResultCleanMixin,
                                             TestDataSpec_clean_result_dict):
    """Like TestDataSpec_clean_result_dict but for a DataSpec subclass."""

    def test_several_invalid_values(self):
        given_dict = self._given_dict(**{
            u'id': u'aaaaa',            # 'aaaaa' is too long
            u'justnew': 'xyz\xdd,123',  # non-UTF-8 value
            # too long label in domain name:
            u'fqdn': (u'www.ołówekkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk'
                      u'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk'
                      u'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.EXAMPLĘ.com'),
        })
        with self.assertRaises(ResultValueCleaningError) as cm:
            self.ds.clean_result_dict(given_dict)
        exc = cm.exception
        self.assertEqual(sorted(exc.error_info_seq), sorted([
            (u'id', u'aaaaa', ANY),
            (u'justnew', 'xyz\xdd,123', ANY),
            (u'fqdn', ANY, ANY),
        ]))
        self.assertTrue(all(isinstance(info[2], Exception)
                            for info in exc.error_info_seq))


class TestDataSpecSubclass_clean_result_keys(SubclassResultCleanMixin,
                                             TestDataSpec_clean_result_keys):
    """Like TestDataSpec_clean_result_keys but for a DataSpec subclass."""


class TestDataSpecSubclass_result_field_specs(SubclassResultCleanMixin,
                                              TestDataSpec_result_field_specs):
    """Like TestDataSpec_result_field_specs but for a DataSpec subclass."""


#
# Others:

class TestDataSpecSubclass__field_custom_info(SubclassMixinBase,
                                              unittest.TestCase):

    def _selftest_assertions(self):
        pass

    def test(self):
        self.assertEqual(self.ds.url.custom_info, dict(
            tralala=dict(ham='spam'),
        ))

    def test_ext(self):
        class AnotherDataSpec(self.data_spec_class):
            url = Ext(                       # extended
                custom_info=Ext(             #  extended
                    tralala=Ext(             #   extended
                        blabla=123,
                    ),
                    foo='bar',
                ),
            )
        ads = AnotherDataSpec()
        self.assertEqual(ads.url.custom_info, dict(
            tralala=dict(
                ham='spam',
                blabla=123,
            ),
            foo='bar',
        ))
