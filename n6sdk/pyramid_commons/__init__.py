# -*- coding: utf-8 -*-

# Copyright (c) 2013-2014 NASK. All rights reserved.

"""
.. note::

   Most of the classes defined in this module are not fully documented
   yet.  For basic information how to use them (or at least most of
   them) -- please consult the :ref:`tutorial`.
"""


import functools
import itertools
import logging

from pyramid.config import Configurator
from pyramid.decorator import reify
from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPForbidden,
    HTTPServerError,
    HTTPNotFound,
)
from pyramid.response import Response
from pyramid.security import (
    #ALL_PERMISSIONS,
    Allow,
    Authenticated,
    Everyone,
)

from n6sdk.class_helpers import attr_required
from n6sdk.data_spec import BaseDataSpec
from n6sdk.exceptions import (
    DataAPIError,
    AuthorizationError,
    ParamCleaningError,
    ResultCleaningError,
    TooMuchDataError
)
from n6sdk.pyramid_commons import renderers as standard_stream_renderers


LOGGER = logging.getLogger()



#
# Auxiliary constants

DUMMY_PERMISSION = "dummy_permission"
DEFAULT_HTTP_METHODS = ('GET',)



#
# Basic classes

class DefaultRootFactory(object):

    """
    A Pyramid-URL-dispatch-related class.

    Typically, when using *n6sdk*, you do not need to bother about it.
    """

    __acl__ = [
        #(Allow, "group:admin", ALL_PERMISSIONS),
        (Allow, Authenticated, DUMMY_PERMISSION),
    ]

    def __init__(self, request):
        self.request = request



class StreamResponse(Response):

    """
    A *response* class used to serve streamed HTTP responses to client queries.

    Constructor args/kwargs:
        `data_generator`:
            An iterator/generator (being a data backend API's method
            call result) that yields subsequent result dictionaries.
        `renderer_name`:
            The name of the stream renderer to be used to render the
            response (e.g., ``'json'``).  The renderer should have been
            registered -- see the documentation of
            :func:`register_stream_renderer`.
        `request`:
            A Pyramid *request* object.
    """

    def __init__(self, data_generator, renderer_name, request):
        super(StreamResponse, self).__init__(conditional_response=True)
        renderer_factory = registered_stream_renderers[renderer_name]
        self.stream_renderer = renderer_factory(data_generator, request)
        self.content_type = self.stream_renderer.content_type
        app_iter = self.stream_renderer.generate_content()
        self.app_iter = app_iter



class DefaultStreamViewBase(object):

    resource_id = None
    renderers = None
    data_spec = None
    data_backend_api_method = None

    #: Can be set to False in a subclass to skip result
    #: records that could not be cleaned (by default
    #: :exc:`pyramid.httpexceptions.HTTPServerError` is raised).
    break_on_result_cleaning_error = True

    @classmethod
    def concrete_view_class(cls, resource_id, renderers, data_spec,
                            data_backend_api_method):
        """
        Create a concrete view subclass (for a particular REST API resource).

        This method is called automatically (by
        :meth:`HttpResource.configure_views`).

        Args/kwargs:
            `resource_id` (string):
                The identified of the HTTP resource (as given as the
                first argument for the :class:`HttpResource` costructor).
            `renderers` (:class:`frozenset` of strings):
                Names of available stream renderers (each of them should
                have been registered -- see the documentation of
                :func:`register_stream_renderer`).
            `data_spec` (instance of a :class:`.BaseDataSpec` subclass):
                The data spec object used to validate and adjust query
                parameters and output data.
            `data_backend_api_method` (string):
                The name of a data backend API method to be called by the view.

        Returns:
            A concrete subclass of the class.

        Raises:
            :exc:`~exceptions.ValueError`:
                If any of the `renderers` has not been registered.
            :exc:`~exceptions.TypeError`:
                If `data_spec` is a class and not an instance of a
                data specification class.
        """

        illegal_renderers = renderers - registered_stream_renderers.viewkeys()
        if illegal_renderers:
            raise ValueError(
                'the following stream renderers have not been registered: ' +
                ', '.join(sorted(map(repr, illegal_renderers))))

        if isinstance(data_spec, type) and issubclass(data_spec, BaseDataSpec):
            raise TypeError(
                'a BaseDataSpec *subclass* has been passed but an '
                '*instance* of a BaseDataSpec subclass is needed')

        _resource_id = resource_id
        _renderers = renderers
        _data_spec = data_spec
        _data_backend_api_method = data_backend_api_method

        class view_class(cls):
            resource_id = _resource_id
            renderers = _renderers
            data_spec = _data_spec
            data_backend_api_method = _data_backend_api_method

        view_class.__name__ = '_{0}_subclass_for_{1}'.format(
              cls.__name__,
              data_backend_api_method)

        return view_class


    @attr_required('resource_id', 'renderers', 'data_spec', 'data_backend_api_method')
    def __init__(self, context, request):
        self.request = request

    @reify
    def renderer_name(self):
        renderer_name = self.request.matchdict.get('renderer', None)
        if renderer_name not in self.renderers:
            raise HTTPNotFound
        return renderer_name

    def __call__(self):
        self.params = self.prepare_params()
        data_generator = self.call_api()
        return StreamResponse(data_generator, self.renderer_name, self.request)

    def prepare_params(self):
        param_dict = dict(self.iter_deduplicated_params())
        clean_param_dict_kwargs = self.get_clean_param_dict_kwargs()
        try:
            return self.data_spec.clean_param_dict(
                param_dict,
                **clean_param_dict_kwargs)
        except AuthorizationError as exc:
            LOGGER.debug('Authorization not successful: %r', exc)
            raise HTTPForbidden(exc.public_message)
        except ParamCleaningError as exc:
            LOGGER.debug('Request parameters not valid: %r', exc)
            raise HTTPBadRequest(exc.public_message)
        except DataAPIError as exc:
            LOGGER.exception('Data backend API error: %r', exc)
            raise HTTPServerError(exc.public_message)

    def iter_deduplicated_params(self):
        chain_iterables = itertools.chain.from_iterable
        params = self.request.params
        for key in params:
            values = params.getall(key)
            assert values and all(isinstance(val, basestring) for val in values)
            yield key, list(chain_iterables(val.split(',') for val in values))

    def call_api(self):
        api_method_name = self.data_backend_api_method
        api_method = getattr(self.request.registry.data_backend_api, api_method_name, None)
        if api_method is None:
            LOGGER.exception('Data backend API has no method %r', api_method_name)
            raise HTTPServerError
        clean_result_dict = self.data_spec.clean_result_dict
        clean_result_dict_kwargs = self.get_clean_result_dict_kwargs()
        try:
            for result_dict in self.call_api_method(api_method):
                try:
                    yield clean_result_dict(
                        result_dict,
                        **clean_result_dict_kwargs)
                except ResultCleaningError as exc:
                    if self.break_on_result_cleaning_error:
                        raise
                    else:
                        LOGGER.error(
                            'Some results not yielded due '
                            'to the cleaning error: %r', exc)
        except AuthorizationError as exc:
            LOGGER.debug('Authorization not successful: %r', exc)
            raise HTTPForbidden(exc.public_message)
        except TooMuchDataError as exc:
            LOGGER.debug('Too much data requested: %r', exc)
            raise HTTPForbidden(exc.public_message)
        except ResultCleaningError as exc:
            LOGGER.exception('Result cleaning error: %r', exc)
            raise HTTPServerError(exc.public_message)
        except DataAPIError as exc:
            LOGGER.exception('Data backend API error: %r', exc)
            raise HTTPServerError(exc.public_message)

    def call_api_method(self, api_method):
        return api_method(
            self.request.auth_data,
            self.params,
            **self.get_extra_api_kwargs())

    def get_clean_param_dict_kwargs(self):
        return {}

    def get_clean_result_dict_kwargs(self):
        return {}

    def get_extra_api_kwargs(self):
        return {}



class HttpResource(object):

    """
    A class of containers of REST API resource properties.

    Required constructor arguments (all of them are keyword-only!):
        `resource_id` (string):
            The identified of the HTTP resource.
            It will be used as the Pyramid route name.
        `url_pattern` (string):
            A URL path pattern ending with the ``.{renderer}``
            placeholder.  Example value:
            ``"/some-url-path/incidents.{renderer}"``.
        `renderers` (string or iterable of strings):
            Names of available stream renderers (each of them should
            have been registered -- see the documentation of
            :func:`register_stream_renderer`).  Example value:
            ``("json", "sjson")``.
        `data_spec` (instance of a :class:`.BaseDataSpec` subclass):
            The data specification object used to validate and adjust
            query parameters and output data.
        `data_backend_api_method` (string):
            The name of the data backend api method to be called by the
            view.

    Optional constructor arguments (all of them are keyword-only!):
        `view_base` (:class:`DefaultStreamViewBase` subclass):
            The base class of the view; default:
            :class:`DefaultStreamViewBase`.
        `http_methods` (string or iterable of strings):
            Names of HTTP methods enabled for the resource; default:
            tuple ``('GET',)``.
        `parmission`:
            An object representing a Pyramid permission; default:
            string ``"dummy_permission"``.

    .. seealso::

       * :meth:`DefaultStreamViewBase.concrete_view_class`,
       * :class:`ConfigHelper`.
    """

    def __init__(self, resource_id,
                 url_pattern,
                 renderers,
                 data_spec,
                 data_backend_api_method,
                 view_base=DefaultStreamViewBase,
                 http_methods=DEFAULT_HTTP_METHODS,
                 permission=DUMMY_PERMISSION,
                 **kwargs):
        self.resource_id = resource_id
        if not url_pattern.endswith('.{renderer}'):
            LOGGER.exception("url_pattern must contain '.{renderer}' suffix")
            raise HTTPServerError
        self.url_pattern = url_pattern
        self.renderers = (
            frozenset([renderers]) if isinstance(renderers, basestring)
            else frozenset(renderers))
        self.data_spec = data_spec
        self.data_backend_api_method = data_backend_api_method
        self.view_base = view_base
        self.http_methods = (
            (http_methods,) if isinstance(http_methods, basestring)
            else tuple(http_methods))
        self.permission = permission
        return super(HttpResource, self).__init__(**kwargs)

    def configure_views(self, config):
        """
        Automatically called by :meth:`ConfigHelper.make_wsgi_app` or
        :meth:`ConfigHelper.complete`.
        """
        route_name = self.resource_id
        view_class = self.view_base.concrete_view_class(
            self.resource_id,
            self.renderers,
            self.data_spec,
            self.data_backend_api_method,
        )
        config.add_route(route_name, self.url_pattern)
        config.add_view(
            view=view_class,
            route_name=route_name,
            request_method=self.http_methods,
            permission=self.permission,
        )



#
# Application startup/configuration

class ConfigHelper(object):

    """
    Class of an object that automatizes necessary WSGI app setup steps.

    Typical usage in your Pyramid application's ``__init__.py``:

    .. code-block:: python

        RESOURCES = <list of HttpResource instances>

        def main(global_config, **settings):
            helper = ConfigHelper(
                settings,
                data_backend_api_class=MyDataBackendAPI,
                authentication_policy=MyCustomAuthenticationPolicy(settings),
                resources=RESOURCES,
            )
            ...  # <- here you can call any methods of the helper.config object
            ...  #    which is a pyramid.config.Configurator instance
            return helper.make_wsgi_app()
    """

    #: (overridable attribute)
    default_static_view_config = None

    #: (overridable attribute)
    default_root_factory = DefaultRootFactory

    def __init__(self,
                 # note: all the arguments should be passed as keyword arguments
                 settings,
                 data_backend_api_class,
                 authentication_policy,
                 resources,
                 static_view_config=None,
                 root_factory=None,
                 **rest_configurator_kwargs):
        self.settings = self.prepare_settings(settings)
        self.data_backend_api_class = data_backend_api_class
        self.authentication_policy = authentication_policy
        self.resources = resources
        if static_view_config is None:
            static_view_config = self.default_static_view_config
        self.static_view_config = static_view_config
        if root_factory is None:
            root_factory = self.default_root_factory
        self.root_factory = root_factory
        self.rest_configurator_kwargs = rest_configurator_kwargs
        self.config = self.prepare_config(self.make_config())
        self._completed = False

    def make_wsgi_app(self):
        if not self._completed:
            self.complete()
        return self.config.make_wsgi_app()

    # overridable/extendable methods:

    def prepare_settings(self, settings):
        return dict(settings)

    def make_config(self):
        return Configurator(
              settings=self.settings,
              authentication_policy=self.authentication_policy,
              root_factory=self.root_factory,
              **self.rest_configurator_kwargs)

    def prepare_config(self, config):
        config.registry.data_backend_api = self.make_data_backend_api()
        config.add_request_method(self.authentication_policy.get_auth_data,
                                  'auth_data', reify=True)
        return config

    def make_data_backend_api(self):
        return self.data_backend_api_class(settings=self.settings)

    def complete(self):
        for res in self.resources:
            res.configure_views(self.config)
        if self.static_view_config:
            self.config.add_static_view(**self.static_view_config)
        self._completed = True



#
# Stream renderer registration

registered_stream_renderers = {}


def register_stream_renderer(name, renderer_factory=None, allow_replace=False):
    """
    Register a stream renderer factory under the specified name.

    Args:
        `name` (:class:`str`):
            The name of the renderer.
        `renderer_factory` (callable object):
            A callable that takes two positional arguments:
            `data_generator` and `request` (see the documentation of
            :class:`StreamResponse` for the description of them),
            and returns a stream renderer.  Stream renderer is an
            iterable that yields consecutive parts of the response
            for WSGI's :meth:`app_iter`.  It is different than Pyramid
            renderers.
        `allow_replace` (:class:`bool`; default: :obj:`False`):
            If set to true you can replace a renderer factory with
            another one.

    Raises:
        :exc:`~exceptions.RuntimeError`:
            If `name` has been already used and `allow_replace` is not true.

    Basic usage:

    .. code-block:: python

        register_stream_renderer(<renderer name>, <renderer factory>)

    or:

    .. code-block:: python

        @register_stream_renderer(<renderer name>)
        def make_my_renderer(data_generator, request):
            ...

    or:

    .. code-block:: python

        @register_stream_renderer(<renderer name>)
        class MyRenderer(...):
            def __init__(self, data_generator, request):
                ...
            ...
    """
    if renderer_factory is None:
        return functools.partial(
            register_stream_renderer,
            name, allow_replace=allow_replace)
    if name in registered_stream_renderers and not allow_replace:
        raise RuntimeError('renderer {0!r} already registered'.format(name))
    registered_stream_renderers[name] = renderer_factory
    return renderer_factory


register_stream_renderer('json', standard_stream_renderers.StreamRenderer_json)
register_stream_renderer('sjson', standard_stream_renderers.StreamRenderer_sjson)



#
# Authentication policies

class BaseAuthenticationPolicy(object):

    """
    The base class for authentication policy classes.

    See: http://docs.pylonsproject.org/projects/pyramid/en/\
latest/narr/security.html#creating-your-own-authentication-policy
    """

    def unauthenticated_userid(self, request):
        raise NotImplementedError(
            'abstract method unauthenticated_userid() not implemented')

    @staticmethod
    def get_auth_data(request):
        """
        Determines the value that will be set as the :attr:`auth_data` of
        the `request` object.

        This function is used as a `request` method that provides the
        :attr:`auth_data` `request` attribute (see:
        :meth:`ConfigHelper.prepare_config` above), which means that
        this function is called *after* :meth:`unauthenticated_userid`
        and *before* meth:`authenticated_userid`.

        It should be implemented as a *static method*.

        Concrete implementation of this method will probably make use
        of the :attr:`unauthenticated_userid` attribute of `request`
        (in older versions of Pyramid the
        :func:`unauthenticated_userid` function from the
        :mod:`pyramid.security` module was used instead of that
        attribute).

        Returns:
            Authentication data (in an application-specific format).
            The default implementation returns :obj:`None`.
        """
        return None

    def authenticated_userid(self, request):
        """
        Concrete implementation of this method will probably make use of
        the :attr:`auth_data` attribute of `request`.  (The value of
        that attribute is produced by the :meth:`get_auth_data`
        method.)
        """
        return None

    def effective_principals(self, request):
        effective_principals = [Everyone]
        if request.auth_data is not None:
            effective_principals.append(Authenticated)
        return effective_principals

    def forget(self, request):
        """
        Can be left dummy if users are recognized externally, e.g. by SSL cert.
        """

    def remember(self, request, principal, **kw):
        """
        Can be left dummy if users are recognized externally, e.g. by SSL cert.
        """



class AnonymousAuthenticationPolicy(BaseAuthenticationPolicy):

    """
    A dummy authentication policy: authenticates everybody (as
    ``"anonymous"``).

    It sets, for all requests, the *user id* and the *authentication
    data* to the string ``"anonymous"``.
    """

    def unauthenticated_userid(self, request):
        return "anonymous"

    @staticmethod
    def get_auth_data(request):
        return request.unauthenticated_userid   # just string "anonymous"

    def authenticated_userid(self, request):
        return request.auth_data                # just string "anonymous"
