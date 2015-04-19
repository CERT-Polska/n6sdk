N6SDK and its `BasicExample`
============================

NOTE: this file contains a brief tutorial.  For more information,
especially a much longer N6SDK tutorial, please refer to the actual
N6SDK documentation (see the README.rst file in the top-level N6SDK
source code directory).



Introductory information
------------------------

The N6SDK library needs Python 2.7.

The N6SDK library makes use of the Pyramid web framework (to learn
more about development and configuration of Pyramid-based projects --
see:
http://docs.pylonsproject.org/projects/pyramid/en/latest/index.html).



Installation for development
----------------------------

It is recommended to use virtualenv
(see: http://virtualenv.readthedocs.org/en/latest/virtualenv.html)
-- especially to avoid collisions with system packages.

1. Install the `virtualenv` package.  On Debian the command is:
> sudo apt-get install python-virtualenv

2. Create and activate a virtualenv:
> virtualenv myvenv
> source myvenv/bin/activate

3. Install N6SDK:
> cd <the main N6SDK source directory>
> python setup.py install

4. Install BasicExample (or your code, maybe somehow based on
BasicExample) for development:
> cd examples/BasicExample
> python setup.py develop

5. Start a test server:
> pserve development.ini

6. In a web browser go to any of the example URLs listed below.

Examples of valid query URLs:

http://127.0.0.1:6543/incidents.json
http://127.0.0.1:6543/incidents.json?ip=11.22.33.44
http://127.0.0.1:6543/incidents.json?category=phish
http://127.0.0.1:6543/incidents.json?category=my-custom-category
http://127.0.0.1:6543/incidents.json?category=my-custom-category&ip=11.22.33.44
http://127.0.0.1:6543/incidents.json?category=bots&category=dos-attacker
http://127.0.0.1:6543/incidents.json?category=bots,dos-attacker,phish,my-custom-category
http://127.0.0.1:6543/incidents.json?time=2014-04-01T10:00
http://127.0.0.1:6543/incidents.sjson?time=2014-04-01T10:00,2014-04-01T23:59:59,2015-05-05T13:13
http://127.0.0.1:6543/incidents.sjson?category=bots,dos-attacker,phish,my-custom-category&confidence=medium,high,low&time=2014-04-01T10:00,2014-04-01T23:59:59
http://127.0.0.1:6543/incidents.sjson?time=2014-04-01T10:00:00.000
http://127.0.0.1:6543/incidents.sjson?mac_address=00:11:22:33:44:55
http://127.0.0.1:6543/incidents.sjson?source=test.first
http://127.0.0.1:6543/incidents.sjson?source=some.non-existent

Examples of invalid query URLs:

http://127.0.0.1:6543/incidents
http://127.0.0.1:6543/incidents.json?some-illegal-key=1&another-one=foo
http://127.0.0.1:6543/incidents.json?category=wrong
http://127.0.0.1:6543/incidents.json?category=bots,dos-attacker,wrong
http://127.0.0.1:6543/incidents.json?category=bots&category=wrong
http://127.0.0.1:6543/incidents.json?ip=11.22.33.44.55
http://127.0.0.1:6543/incidents.sjson?ip=11.22.33.444
http://127.0.0.1:6543/incidents.sjson?mac_address=00:11:123456:33:44:55
http://127.0.0.1:6543/incidents.sjson?time=blablabla
http://127.0.0.1:6543/incidents.sjson?time=2014-13-13T10:00:00
http://127.0.0.1:6543/incidents.sjson?time=2014-04-01T10:00,2014-13-13T10:00:00



Installation for production (on Apache server)
----------------------------------------------

1. Create directory structure for your server, e.g. under /opt:
> mkdir /opt/myn6sdk_server

2. Copy the main N6SDK source directory to /opt/myn6sdk_server/

3. Copy the examples/BasicExample directory (or the directory
containing your code) to /opt/myn6sdk_server/

4. Install the `virtualenv` package (if it is not installed yet).
On Debian the command is:
> sudo apt-get install python-virtualenv

5. Create and activate a virtualenv for production:
> virtualenv /opt/myn6sdk_server/venv
> source /opt/myn6sdk_server/venv/bin/activate

6. Install N6SDK for production:
> cd /opt/myn6sdk_server/<N6SDK source directory name (see point 2.)>
> python setup.py install

7. Install BasicExample (or your code) for production:
> cd /opt/myn6sdk_server/BasicExample
> python setup.py install

8. Modify /opt/myn6sdk_server/BasicExample/production.ini to match
your environment (consult the Pyramid documentation for details).

9. Create a wsgi script for your application within the virtualenv
directory (/opt/myn6sdk_server/venv/myn6sdkapp.wsgi) containing the
following code:

from pyramid.paster import get_app, setup_logging
ini_path = '/opt/myn6sdk_server/BasicExample/production.ini'
setup_logging(ini_path)
application = get_app(ini_path, 'main')

10. Create Python egg cache; the Apache's user (on Debian the user name
is "www-data") must have write access to the egg cache's directory:

> mkdir /opt/myn6sdk_server/.python-eggs
> chown www-data /opt/myn6sdk_server/.python-eggs

11. Edit your Apache configuration and add BasicExample application
(or your application) to the configuration.  On Debian application
configuration files are usually placed in the
/etc/apache2/sites-available/ directory.  Created configuration file
should then be symlinked to /etc/apache2/sites-enabled/

Example configuration:

<VirtualHost *:80>
        # Only one Python sub-interpreter should be used
        # (multiple ones do not cooperate well with C extensions).
        WSGIApplicationGroup %{GLOBAL}

        # Remove the following line if you use native Apache authorisation.
        WSGIPassAuthorization On

        WSGIDaemonProcess myn6sdk_server \
           python-path=/opt/myn6sdk_server/venv/lib/python2.7/site-packages \
           python-eggs=/opt/myn6sdk_server/.python-eggs
        WSGIScriptAlias /myn6sdk /opt/myn6sdk_server/venv/myn6sdkapp.wsgi

        <Directory /opt/myn6sdk_server/venv>
          WSGIProcessGroup myn6sdk_server
          Order allow,deny
          Allow from all
        </Directory>

        # Logging of errors and other events:
        ErrorLog ${APACHE_LOG_DIR}/error.log
        # Possible values for the LogLevel directive include:
        # debug, info, notice, warn, error, crit, alert, emerg.
        LogLevel warn

        # Logging of client requests:
        CustomLog ${APACHE_LOG_DIR}/access.log combined

        # It is recommended to uncomment and adjust the following line.
        #ServerAdmin webmaster@yourserver.example.com
</VirtualHost>

You may also need to disable the default Apache site, e.g. by removing
the /etc/apache2/sites-enabled/000-default symbolic link.

12. Restart Apache.  Your app should now be being served.
Please, try with a web browser the URL:
http://your.apache.server/myn6sdk/incidents.json



Developing with N6SDK
---------------------

At the minimum, the application and its HTTP resources need to be set
up in the project's __init__.py file as well as an implementation of
DataBackendAPI must be provided (see: the following subsections).

Optionally, the n6sdk.data_spec.DataSpec and
n6sdk.pyramid_commons.HttpResource classes may be
extended (see: the following subsections and examples in
examples/BasicExample/basic_example/custom.py) to customize some
application behaviours.

Defining your custom authentication policy (as a subclass of
n6sdk.pyramid_commons.BaseAuthenticationPolicy) is also possible
(see: the following subsections as well as docstrings of the
BaseAuthenticationPolicy class defined in
n6sdk/pyramid_commons/__init__.py).



Project's __init__.py file
..........................

Here (in the <your project's package>/__init__.py file) you configure
resources and URLs, and set up the application.

Below we present an example similar to the contents of the
examples/BasicExample/basic_example/__init__.py file -- with
additional comments:


from n6sdk.pyramid_commons import (
    AnonymousAuthenticationPolicy,  # alternatively, you can create your custom implementation of auth policy...
    ConfigHelper,
)

from .custom import (     # importing your custom classes here
    CustomDataSpec,         # alternatively, you can use standard DataSpec directly (importable from n6sdk.data_spec)
    CustomHttpResource,     # alternatively, you can use standard HttpResource directly (importable from n6sdk.pyramid_commons)
    DataBackendAPI,         # your own implementation of the data backend API (mandatory!)
)

# (we'll need to pass an instance, not the class itself; the same instance can be used with more than one http resource)
custom_data_spec = CustomDataSpec()

# define REST API resources here, each referring to a particular kind of data query
RESOURCES = [
    CustomHttpResource(
        # note: all arguments as keyword arguments:
        resource_id='/incidents',               # unique id - can be used e.g. to evaluate permissions, usage depends on implementer
        url_pattern='/incidents.{renderer}',    # url path used to access the resource, .{renderer} placeholder is mandatory
        renderers=('json', 'sjson'),            # renderers available for this resource (json and sjson are provided out-of-the-box)
        data_spec=custom_data_spec,             # data spec instance used to validate query params and output data
        data_backend_api_method='select_incidents',     # name of DataBackendAPI's method that will be called for this resource
        example_dummy_feature='foo',                    # example custom extension implemented in CustomHttpResource
    ),
]       # ^ See also n6sdk.pyramid_commons.HttpResource's code for info about additional parameters with default values

def main(global_config, **settings):
    helper = ConfigHelper(
        # note: all arguments as keyword arguments:
        settings=settings,
        data_backend_api_class=DataBackendAPI,                   # DataBackendAPI class used by all resources
        authentication_policy=AnonymousAuthenticationPolicy(),   # Auth policy instance, use custom implementation if needed
        resources=RESOURCES,
    )
        # ^ See also n6sdk.pyramid_commons.ConfigHelper's code for info about additional parameters and attributes...
    # ---
    # --- here you could (optionally) add some stuff to the
    # --- helper's `config` attribute (which is a pyramid.config.Configurator instance)...
    # ---
    return helper.make_wsgi_app()



The <some your module>.DataBackendAPI class
...........................................

This class is used to implement data querying.  An appropriate method
of this class is called when accessing a resource (configured in your
application's __init__.py file: data_backend_api_method=<method_name>
-- see the code example in the subsection "Project's __init__.py file"
above).

It is recommended to decorate your DataBackendAPI class with the
@n6sdk.class_helpers.singleton decorator.

DataBackendAPI's __init__() must accept the `settings` argument.

Each of the actual data backend API methods should:

* take two positional arguments: `auth_data` and `params` (described in
  the code example below); it can also take some additional keyword
  arguments (then you may need to implement the get_extra_api_kwargs()
  method in your custom DefaultStreamViewBase subclass).

* be a generator function or return an iterator or a generator; it
  should yield events (aka incident data items, aka result dicts) one
  by one in a format that conforms to the DataSpec subclass used (each
  dict will be passed through <data spec>.clean_result_dict()).

A stub DataBackendAPI implementation example:


from n6sdk.class_helpers import singleton

@singleton
class DataBackendAPI(object):

    def __init__(self, settings):
        pass

    def get_events(self, auth_data, params):
        """
        Args:
            `auth_data`:
                Data in a custom format that may be used by DataBackendAPI,
                for example, to evaluate permissions.
            `params` (dict):
                Query parameters (used to query the database) sent by
                the user/browser and (already) cleaned with the
                <data spec>.clean_param_dict() method.

        Yields:
            Events (aka result dicts -- each ready to be passed in to the
            <data spec>.clean_result_dict() method).
        """
        yield {'event field...': 'some value...'}


See also: more interesting implementation example in the
examples/BasicExample/basic_example/custom.py file.



n6sdk.data_spec.DataSpec and n6sdk.data_spec.fields.Field subclasses
....................................................................

The DataSpec class defines the basic specification of:

* query parameters a client can/should specify in a query, i.e.:
  * the set of legal query keys (parameter names);
  * several properties of each query parameter, especially:
    * whether the parameter is required or optional,
    * how its values are cleaned (adjusted and validated) before
      being passed into the data backend API (e.g., that a 'time.min'
      value must be a string being a valid ISO-8601-formatted
      date+time that will be converted to Python datetime.datetime,
      and that timezone-aware values will be translated to UTC and
      represented by "naive" [timezone-less] datetime.datetime objects);

* items a data backend API can/should provide in each result
  data dictionary (containing data of an incident a user query
  refers to), i.e.:
  * the set of legal result keys;
  * several properties of each result item, especially:
    * whether the item is required or optional,
    * how its values are cleaned (adjusted and validated) before
      being passed into a renderer/JSON-serializer/etc. (e.g.,
      that a 'time' value must be either a datetime.datetime object or
      a string being a valid ISO-8601-formatted date+time that will be
      converted to datetime.datetime object, and that timezone-aware
      values will be translated to UTC and represented by "naive"
      [timezone-less] datetime.datetime objects).

The cleaning mechanisms are invoked automatically by N6SDK library's
mechanisms (by appropriate n6sdk.pyramid_commons.DefaultStreamViewBase
methods).

The way of defining the data specification is somewhat similar
to those known from the Django's or SQLAlchemy's ORMs -- a data
specification class (DataSpec or its subclass) is like a "model"
and particular query/result item specifications (Field subclass
instances) are like "fields" or "columns".

You can define your own data spec class (as a DataSpec subclass)
as well as your own Field subclasses.

See:
* examples/BasicExample/basic_example/custom.py (CustomDataSpec)
* n6sdk/data_spec/__init__.py (DataSpec, BaseDataSpec and Ext)
* n6sdk/data_spec/fields.py (Field and its subclasses)



n6sdk.pyramid_commons.HttpResource or its custom subclass(es)
.............................................................

You instantiate it to specify properties of a particular resource
(REST API URL path such as '/incidents.json') -- see the code example
in the "Project's __init__.py file" subsection above.

See also: a simple subclassing example in the
examples/BasicExample/basic_example/custom.py file.



The authentication policy class
...............................

Generally, the authentication policy class should be implemented as
described on the
http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html#creating-your-own-authentication-policy
web page -- except that the N6SDK library requires that the policy
class has the additional static (decorated with staticmethod()) method
get_auth_data() that takes exactly one positional argument: a Pyramid
request object.  The method is expected to return a value that is not
None in case of authentication success, and None otherwise.  Apart
from this simple rule there are no constraints what exactly the return
value should be -- the implementer decides about that.  The return
value will be available as the `auth_data` attribute of the Pyramid
request as well as is passed into data backend API methods as the
`auth_data` argument.

The N6SDK library provides BaseAuthenticationPolicy -- an authentication
policy base class that makes it easier to implement your own
authentication policies.

See: n6sdk/pyramid_commons/__init__.py (BaseAuthenticationPolicy).
