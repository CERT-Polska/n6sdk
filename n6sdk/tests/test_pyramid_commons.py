# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.


import unittest

from mock import (
    call,
    MagicMock,
    patch,
    sentinel as sen,
)
from pyramid.httpexceptions import (
    HTTPForbidden,
    HTTPServerError,
)

from n6sdk.exceptions import (
    DataAPIError,
    AuthorizationError,
    ResultCleaningError,
)
from n6sdk.pyramid_commons import (
    DefaultStreamViewBase,
)


@patch('n6sdk.pyramid_commons.registered_stream_renderers',
       new={'some': MagicMock(), 'another': MagicMock()})
class TestDefaultStreamViewBase__concrete_view_class(unittest.TestCase):

    def test_with_args(self, *args):
        result = DefaultStreamViewBase.concrete_view_class(
            'some_resource_id',
            frozenset({'some'}),
            sen.data_spec,
            'some_method_name')
        self._basic_asserts(result)

    def test_with_kwargs(self, *args):
        result = DefaultStreamViewBase.concrete_view_class(
            resource_id='some_resource_id',
            renderers=frozenset({'some'}),
            data_spec=sen.data_spec,
            data_backend_api_method='some_method_name')
        self._basic_asserts(result)

    def test_for_subclass(self, *args):
        class SomeViewBase(DefaultStreamViewBase):
            x = 42
        result = SomeViewBase.concrete_view_class(
            resource_id='some_resource_id',
            renderers=frozenset({'some'}),
            data_spec=sen.data_spec,
            data_backend_api_method='some_method_name')
        self._basic_asserts(result)
        self.assertTrue(issubclass(result, SomeViewBase))
        self.assertEqual(result.x, 42)

    def _basic_asserts(self, result):
        self.assertTrue(issubclass(result, DefaultStreamViewBase))
        self.assertIsNot(result, DefaultStreamViewBase)
        self.assertEqual(
            result.__name__,
            '_{base_class_name}_subclass_for_some_method_name'.format(
                base_class_name=result.__mro__[1].__name__))
        self.assertEqual(result.resource_id, 'some_resource_id')
        self.assertEqual(result.renderers, {'some'})
        self.assertIs(result.data_spec, sen.data_spec)
        self.assertEqual(result.data_backend_api_method, 'some_method_name')

    def test_unregistered_renderer_error(self):
        with self.assertRaisesRegexp(ValueError, r'renderer.*not.*registered'):
            DefaultStreamViewBase.concrete_view_class(
                resource_id='some_resource_id',
                renderers=frozenset({'some_unregistered'}),
                data_spec=sen.data_spec,
                data_backend_api_method='some_method_name')


@patch('n6sdk.pyramid_commons.LOGGER')
class TestDefaultStreamViewBase__call_api(unittest.TestCase):

    def setUp(self):
        self.data_spec = MagicMock()
        self.data_spec.clean_result_dict.side_effect = self.cleaned_list = [
            sen.cleaned_result_dict_1,
            sen.cleaned_result_dict_2,
            sen.cleaned_result_dict_3,
        ]
        self.request = MagicMock()
        self.request.registry.data_backend_api.my_api_method = (
            sen.api_method)
        with patch('n6sdk.pyramid_commons.registered_stream_renderers',
                   new={'some': MagicMock()}):
            self.cls = DefaultStreamViewBase.concrete_view_class(
                resource_id='some_resource_id',
                renderers=frozenset({'some'}),
                data_spec=self.data_spec,
                data_backend_api_method='my_api_method')
        self.cls.call_api_method = MagicMock()
        self.cls.call_api_method.return_value = self.call_iter = iter([
            sen.result_dict_1,
            sen.result_dict_2,
            sen.result_dict_3,
        ])
        self.cls.get_clean_result_dict_kwargs = MagicMock(
            return_value={'kwarg': sen.kwarg})
        self.obj = self.cls(sen.context, self.request)
        self.results = []

    def do_call(self):
        result_generator = self.obj.call_api()
        while True:
            try:
                self.results.append(next(result_generator))
            except StopIteration:
                break

    def test_full_success(self, LOGGER):
        self.do_call()
        self.cls.get_clean_result_dict_kwargs.assert_called_once_with()
        self.cls.call_api_method.assert_called_once_with(sen.api_method)
        self.assertEqual(self.data_spec.clean_result_dict.mock_calls, [
            call(sen.result_dict_1, kwarg=sen.kwarg),
            call(sen.result_dict_2, kwarg=sen.kwarg),
            call(sen.result_dict_3, kwarg=sen.kwarg),
        ])
        self.assertEqual(self.results, [
            sen.cleaned_result_dict_1,
            sen.cleaned_result_dict_2,
            sen.cleaned_result_dict_3,
        ])

    def test_breaking_on_ResultCleaningError(self, LOGGER):
        assert self.cls.break_on_result_cleaning_error
        self.cleaned_list[1] = ResultCleaningError
        with self.assertRaises(HTTPServerError):
            self.do_call()
        self.cls.get_clean_result_dict_kwargs.assert_called_once_with()
        self.cls.call_api_method.assert_called_once_with(sen.api_method)
        self.assertEqual(self.data_spec.clean_result_dict.mock_calls, [
            call(sen.result_dict_1, kwarg=sen.kwarg),
            call(sen.result_dict_2, kwarg=sen.kwarg),
        ])
        self.assertEqual(LOGGER.exception.call_count, 1)
        self.assertEqual(self.results, [
            sen.cleaned_result_dict_1,
        ])
        not_comsumed_result_dicts = list(self.call_iter)
        self.assertEqual(not_comsumed_result_dicts, [
            sen.result_dict_3,
        ])

    def test_skipping_ResultCleaningError_if_flag_is_false(self, LOGGER):
        self.cls.break_on_result_cleaning_error = False  # <- this flag
        self.cleaned_list[1] = ResultCleaningError
        self.do_call()
        self.cls.get_clean_result_dict_kwargs.assert_called_once_with()
        self.cls.call_api_method.assert_called_once_with(sen.api_method)
        self.assertEqual(self.data_spec.clean_result_dict.mock_calls, [
            call(sen.result_dict_1, kwarg=sen.kwarg),
            call(sen.result_dict_2, kwarg=sen.kwarg),
            call(sen.result_dict_3, kwarg=sen.kwarg),
        ])
        self.assertEqual(LOGGER.error.call_count, 1)
        self.assertEqual(self.results, [
            sen.cleaned_result_dict_1,
            sen.cleaned_result_dict_3,
        ])

    def test_breaking_on_AuthorizationError(self, LOGGER):
        self.cls.call_api_method.side_effect = AuthorizationError
        with self.assertRaises(HTTPForbidden):
            self.do_call()
        self.cls.get_clean_result_dict_kwargs.assert_called_once_with()
        self.cls.call_api_method.assert_called_once_with(sen.api_method)
        self.assertEqual(self.data_spec.clean_result_dict.call_count, 0)
        self.assertEqual(self.results, [])

    def test_breaking_on_DataAPIError(self, LOGGER):
        self.cls.call_api_method.side_effect = DataAPIError
        with self.assertRaises(HTTPServerError):
            self.do_call()
        self.cls.get_clean_result_dict_kwargs.assert_called_once_with()
        self.cls.call_api_method.assert_called_once_with(sen.api_method)
        self.assertEqual(self.data_spec.clean_result_dict.call_count, 0)
        self.assertEqual(LOGGER.exception.call_count, 1)
        self.assertEqual(self.results, [])


## TODO: more tests...
