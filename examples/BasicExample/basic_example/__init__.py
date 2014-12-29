# -*- coding: utf-8 -*-

from n6sdk.pyramid_commons import (
    AnonymousAuthenticationPolicy,
    ConfigHelper,
)

from .custom import (
    CustomDataSpec,
    CustomHttpResource,
    DataBackendAPI,
)


custom_data_spec = CustomDataSpec()

RESOURCES = [
    CustomHttpResource(
        resource_id='/incidents',
        url_pattern='/incidents.{renderer}',
        renderers=('json', 'sjson'),
        data_spec=custom_data_spec,
        data_backend_api_method='select_incidents',
        example_dummy_feature='foo',
    ),
]

## you can also quite easily configure the static content view...
#STATIC_VIEW_CONFIG = {
#    'name': 'static',
#    'path': 'static',
#    'cache_max_age': 3600,
#}


def main(global_config, **settings):
    helper = ConfigHelper(
        settings=settings,
        data_backend_api_class=DataBackendAPI,
        authentication_policy=AnonymousAuthenticationPolicy(),
        resources=RESOURCES,
        #static_view_config=STATIC_VIEW_CONFIG,
    )
    return helper.make_wsgi_app()
