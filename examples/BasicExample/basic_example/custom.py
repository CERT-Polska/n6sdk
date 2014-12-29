# -*- coding: utf-8 -*-

import datetime

from n6sdk.class_helpers import singleton
from n6sdk.data_spec import DataSpec, Ext
from n6sdk.data_spec.fields import MD5Field, UnicodeRegexField
from n6sdk.exceptions import AuthorizationError
from n6sdk.pyramid_commons import HttpResource



class CustomDataSpec(DataSpec):

    """
    Example custom implementation of DataSpec.

    You can use the standard DataSpec class directly or create its
    subclass -- like this one -- to extend its functionality, especially
    by adding/modifying/replacing/removing particular field specifications.
    """

    # Standard field specifications are defined in n6sdk.data_spec.DataSpec;
    # several examples of extending it:

    # * adding a new field
    mac_address = UnicodeRegexField(
        in_params='optional',  # *can* be in query params
        in_result='optional',  # *can* be in result data

        regex=r'^(?:[0-9A-F]{2}(?:[:-]|$)){6}$',
        error_msg_template=u'"{}" is not a valid MAC address',
    )

    # * modifying (extending) some existing fields
    category = Ext(
        enum_values=DataSpec.category.enum_values + ('my-custom-category',),
    )
    time = Ext(
        in_params='optional',  # here: enabling bare 'time' also for queries
                               # (by default 'time.min' and 'time.max' query
                               # params are allowed but bare 'time' is not)
        extra_params=Ext(
            min=Ext(custom_info=dict(my_data='foo')),  # attaching some arbitrary data
            max=Ext(custom_info=dict(my_data='bar')),  # for possible introspection...
        ),
    )

    # * replacing an existing field with a new one
    id = MD5Field(
        in_params='optional',
        in_result='required',  # *must* be in result data
    )

    # * removing (masking) an existing field
    replaces = None

    # See also the source code and docstrings of:
    # * n6sdk.data_spec.DataSpec
    # * n6sdk.data_spec.fields.Field and its subclasses



class CustomHttpResource(HttpResource):

    """
    Example custom implementation of HttpResource.

    You can use the standard HttpResource class directly or create its
    subclass -- like this one -- to extend its functionality/configurability.
    """

    def __init__(self, example_dummy_feature='foobar', **kwargs):
        self.example_dummy_feature = example_dummy_feature
        super(CustomHttpResource, self).__init__(**kwargs)



@singleton
class DataBackendAPI(object):

    """
    Example data backend.
    """

    _dummy_incident_db = [
        {
            'id': '0123456789abcdef0123456789abcdef',
            'category': 'phish',
            'restriction': 'public',
            'confidence': 'low',
            'source': 'test.first',
            'time': datetime.datetime(2014, 4, 1, 10, 0, 0),
            'mac_address': '00:11:22:33:44:55',
            'url': 'http://example.com/?spam=ham',
            'address': [
                {
                    'ip': '11.22.33.44',
                },
                {
                    'ip': '123.124.125.126',
                    'asn': 12345,
                    'cc': 'US',
                }
            ],
        },
        {
            'id': '123456789abcdef0123456789abcdef0',
            'category': 'my-custom-category',
            'restriction': 'need-to-know',
            'confidence': 'medium',
            'source': 'test.first',
            'time': datetime.datetime(2014, 4, 1, 23, 59, 59),
            'adip': 'x.2.3.4',
        },
        {
            'id': '23456789abcdef0123456789abcdef01',
            'category': 'my-custom-category',
            'restriction': 'public',
            'confidence': 'high',
            'source': 'test.second',
            'time': datetime.datetime(2014, 4, 1, 23, 59, 59),
            'url': 'http://example.com/?spam=ham',
            'address': [
                {
                    'ip': '11.22.33.44',
                },
                {
                    'ip': '111.122.133.144',
                    'asn': 87654321,
                    'cc': 'PL',
                },
            ],
        },
    ]

    def __init__(self, settings):
        """
        Initialize DataBackendAPI using settings...
        """

    def select_incidents(self, auth_data, params):
        if auth_data != 'anonymous':
            raise AuthorizationError(public_message='Who is it?!')
        # this is a dummy and naive implementation -- in a real
        # implementation some kind of database query would need
        # to be performed instead...
        for result in self._dummy_incident_db:
            for key, value_list in params.iteritems():
                if key in ('ip', 'asn', 'cc'):
                    address_seq = result.get('address', [])
                    if not any(addr.get(key) in value_list
                               for addr in address_seq):
                        break
                # *.min/*.max/*.sub/ip.net queries not supported
                # by this naive implementation
                elif result.get(key) not in value_list:
                    break
            else:
                yield result
