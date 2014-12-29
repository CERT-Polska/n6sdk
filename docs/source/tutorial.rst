.. _tutorial:

********
Tutorial
********

This tutorial describes how to use the *n6sdk* library to implement an
*n6*-like REST API that provides access to your own network incident
data source.


.. _setting_up_working_env:

Setting up the development environment
======================================

.. _working_env_prerequisites:

Prerequisites
-------------

You need to have:

* A Linux system + the *bash* shell used to interact with it + basic
  Unix-like OS administrator tools such as *sed* (other platforms and
  tools could also be used, but this tutorial assumes using the
  aforementioned ones) + your favorite text editor;
* Python 2.7 installed;
* the *virtualenv* tool installed (see:
  http://virtualenv.readthedocs.org/en/latest/virtualenv.html; on
  Debian GNU/Linux it can be installed with the command: ``sudo apt-get
  install python-virtualenv``);
* network access;
* unpacked source distribution of the *n6sdk* library.


Providing the necessary files
-----------------------------

We will start with creating a directory for our example project:

.. code-block:: bash

   $ mkdir <the main directory of the project>

(Of course, ``<the main directory of the project>`` needs to be
replaced with the actual name (absolute path) of the directory you
want to create.)

Now, we need to populate the directory with necessary files.  We can
use some of the example files accompanying the *n6sdk* library:

.. code-block:: bash

   $ cd <the main N6SDK source directory>/examples/BasicExample
   $ cp -a setup.py development.ini production.ini MANIFEST.in \
           <the main directory of the project>/

(Of course, ``<the main n6sdk source directory>`` needs to be replaced
with the actual name (absolute path) of the directory containing the
source code of *n6sdk*.)

The files should be customized.  At the absolute minimum, we need to
replace the ``basic_example`` text with the actual name of our
project's package.  In this tutorial it will be ``using_n6sdk`` (you
can, of course, pick another name):

.. code-block:: bash

   $ cd <the main directory of the project>
   $ sed -i -r -e 's/basic_example/using_n6sdk/g' \
         setup.py development.ini production.ini MANIFEST.in

(You may also want to customize other details in these files,
especially the *version* field in the ``setup.py`` file.)

We also need to create the actual Python package (as it was said, in
this tutorial its name will be ``using_n6sdk``):

.. code-block:: bash

   $ mkdir using_n6sdk
   $ touch using_n6sdk/__init__.py


Installing the necessary components
-----------------------------------

Now, we will create and activate our Python *virtual environment*:

.. code-block:: bash

   $ virtualenv dev-venv
   $ source dev-venv/bin/activate

Then, we can install the *n6sdk* library:

.. code-block:: bash

   $ cd <the main N6SDK source directory>
   $ python setup.py install

...as well as our new Python package -- for development (please note
that for this package the setup command will be ``develop``, not
``install``):

.. code-block:: bash

   $ cd <the main directory of the project>
   $ python setup.py develop

We can check whether everything up to now went well by running the
Python interpreter...

.. code-block:: bash

   $ python

...and trying importing some of the installed components:

   >>> import n6sdk
   >>> import n6sdk.data_spec.fields
   >>> n6sdk.data_spec.fields.Field
   <class 'n6sdk.data_spec.fields.Field'>
   >>> import using_n6sdk
   >>> exit()


.. _data_processing_and_arch:

Data processing and architecture overview
=========================================

When a client sends a **HTTP request** to the *n6 REST API*, the
following data processing is performed on the server side:

1. **Receiving the HTTP request**

   *n6sdk* uses the *Pyramid* library (see:
   http://docs.pylonsproject.org/en/latest/docs/pyramid.html) to
   perform processing related to HTTP communication and request
   routing (especially, deciding what function shall be invoked with
   what parameters depending on the given URL), however there are the
   *n6sdk*-specific wrappers and helpers used to configure some
   important factors:
   :class:`n6sdk.pyramid_commons.DefaultStreamViewBase`,
   :class:`n6sdk.pyramid_commons.HttpResource` and
   :class:`n6sdk.pyramid_commons.ConfigHelper` (see below:
   :ref:`gluing_it_together`).  These three classes can be customized
   by subclassing them and extending selected methods, however it is
   beyond the scope of this tutorial.

2. **Authentication**

   Authentication is performed using a mechanism provided by the
   *Pyramid* library: *authentication policies*. The simplest policy
   is implemented as the
   :class:`n6sdk.pyramid_commons.AnonymousAuthenticationPolicy` class
   (it is a dummy policy: all clients are identified as
   ``"anonymous"``); it can be replaced with a custom one (see below:
   :ref:`custom_authn_policy`).

3. **Cleaning query parameters provided by the client**

   Here "cleaning" means: validation and adjustment (normalization) of
   the parameters.  An instance of a *data specification class* (see
   below: :ref:`data_spec_class`) is responsible for doing that.

4. **Retrieving result data from the data backend API**

   The *data backend API*, responsible for interacting with the actual
   data storage, needs to be implemented as a class (see below:
   :ref:`data_backend_api`).

   For a client request, an appropriate method of this class is called
   with authentication data (see above: *2. Optional authentication*)
   and cleaned client query parameters (see above: *3. Cleaning query
   parameters...*) as call arguments.  The result of the call is an
   iterator which yields dictionaries, each containing data of one
   network incident.

5. **Cleaning the result data**

   Each of the yielded dictionaries is cleaned.  Here "cleaning"
   means: validation and adjustment (normalization) of the result
   data.  An instance of a *data specification class* (see below:
   :ref:`data_spec_class`) is responsible for doing that.

   The result is another iterator.

6. **Rendering the HTTP response**

   The yielded cleaned dictionaries are processed to produce
   consecutive fragments of the HTTP response which are successively
   sent to the client.  The key component responsible for transforming
   the dictionaries into the response body is a *renderer*.  Note that
   *n6sdk* renderers (being a custom *n6sdk* concept, different from
   *Pyramid* renderers) are able to process data in an iterator
   ("stream-like") manner, so even if the resultant response body is
   huge it does not have to fit as a whole in the server's memory.

   The *n6sdk* library provides two standard renderers: ``json`` (to
   render JSON-formatted responses) and ``sjson`` (to render responses
   in a format similar to JSON but more convenient for "stream-like"
   or "pipeline" data processing).

   Implementing and registering custom renderers is possible, however
   it is beyond the scope of this tutorial.


.. _data_spec_class:

Data specification class
========================

Basics
------

A *data specification* determines:

* how query (search) parameters from a client (specified as the query
  string part of the URL of a HTTP request) are cleaned before being
  passed in to the data backend API -- that is:

  * what are the legal parameter names;
  * whether particular parameters are required or optional;
  * what are valid values of particular parameters (e.g.: a
    ``time.min`` value must be a valid *ISO-8601*-formatted date and
    time);
  * whether, for a particular parameter, there can be many alternative
    values (comma-separated within a parameter item of the URL's query
    string) or only one value (e.g.: ``time.min`` can have only one
    value, and ``ip`` can have multiple values);
  * how particular parameter values are normalized (e.g.: a
    ``time.min`` value is always transformed to a Python
    :class:`datetime.datetime` object, converting any time zone
    information to UTC);

* how result dictionaries (each containing data of one incident)
  yielded by the data backend API are cleaned before being passed in
  to a response renderer -- that is:

  * what are the legal result keys;
  * whether particular items are required or optional;
  * what are valid types and values of particular items (e.g.: a
    ``time`` value must be either a :class:`datetime.datetime` object
    or a string being a valid *ISO-8601*-formatted date and time);
  * how particular items are normalized (e.g.: a ``time`` value is
    always transformed to a Python :class:`datetime.datetime` object,
    converting any time zone information to UTC).

The declarative way of defining a *data specification* is somewhat
similar to domain-specific languages known from ORMs (such as the
*SQLAlchemy*'s or *Django*'s ones): a data specification class
(:class:`n6sdk.data_spec.DataSpec` or some subclass of it) looks like
an ORM "model" class and particular query parameter and result item
specifications (being instances of
:class:`n6sdk.data_spec.fields.Field` or of subclasses of it) are
declared similarly to ORM "fields" or "columns".

For example, consider the following simplified and shortened version
of the :class:`n6sdk.data_spec.DataSpec` source code::

    class DataSpec(BaseDataSpec):

        id = UnicodeLimitedField(
            in_params='optional',
            in_result='required',
            max_length=64,
        )

        time = DateTimeField(
            in_params=None,
            in_result='required',

            extra_params=dict(
                min=DateTimeField(           # `time.min`
                    in_params='optional',
                    single_param=True,
                ),
                max=DateTimeField(           # `time.max`
                    in_params='optional',
                    single_param=True,
                ),
            ),
        )

        address = AddressField(
            in_params=None,
            in_result='optional',
        )

        ip = IPv4Field(
            in_params='optional',
            in_result=None,

            extra_params=dict(
                net=IPv4NetField(            # `ip.net`
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

        count = IntegerField(
            in_params=None,
            in_result='optional',
            min_value=0,
            max_value=(2 ** 15 - 1),
        )

        ### ...other field specifications...


What do we see above:

1. ``id`` is a text field: its values are strings, not longer than 64
   characters (as its declaration is an instance of
   :class:`n6sdk.data_spec.fields.UnicodeLimitedField` created with
   the constructor argument `max_length` set to ``64``). It is
   **optional** as a query parameter and **required** (obligatory) as
   an item of a result dictionary.

2. ``time`` is a date-and-time field (as its declaration is an
   instance of :class:`n6sdk.data_spec.fields.DateTimeField`). It is
   **not** a legal query parameter, and it is **required** as an item
   of a result dictionary.

3. ``time.min`` and ``time.max`` are date-and-time fields (as their
   declarations are instances of
   :class:`n6sdk.data_spec.fields.DateTimeField`). They are
   **optional** as query parameters, and they are **not** legal items
   of a result dictionary. Unlike most of other fields, these two
   fields do not allow to specify multiple query parameter values
   (note the constructor argument `single_param` set to ``True``).

4. ``address`` is a field whose values are lists of dictionaries
   containing ``ip`` and optionally ``asn`` and ``cc`` (as the
   declaration of ``address`` is an instance of
   :class:`n6sdk.data_spec.fields.AddressField`). It is **not** a
   legal query parameter, and it is **optional** as an item of a
   result dictionary.

5. ``ip`` is an IPv4 address field (as its declaration is an instance
   of :class:`n6sdk.data_spec.fields.IPv4Field`). It is **optional**
   as a query parameter and it is **not** a legal item of a result
   dictionary (note that in a result dictionary the ``address`` field
   contains the corresponding data).

6. ``ip.net`` is an IPv4 network definition (as its declaration is an
   instance of :class:`n6sdk.data_spec.fields.IPv4NetField`). It is
   **optional** as a query parameter and it is **not** a legal item of
   a result dictionary.

7. ``asn`` is an autonomous system number (ASN) field (as its
   declaration is an instance of
   :class:`n6sdk.data_spec.fields.ASNField`). It is **optional** as a
   query parameter and it is **not** a legal item of a result
   dictionary (note that in a result dictionary the ``address`` field
   contains the corresponding data).

8. ``cc`` is 2-letter country code field (as its declaration is an
   instance of :class:`n6sdk.data_spec.fields.CCField`). It is
   **optional** as a query parameter and it is **not** a legal item of
   a result dictionary (note that in a result dictionary the
   ``address`` field contains the corresponding data).

9. ``count`` is an integer field: its values are integer numbers, not
   less than 0 and not greater than 32767 (as the declaration of
   ``count`` is an instance of
   :class:`n6sdk.data_spec.fields.IntegerField` created with the
   constructor arguments: `min_value` set to 0 and `max_value` set to
   32767).  It is **not** a legal query parameter, and it is
   **optional** as an item of a result dictionary.


You may want to create your own custom data specification by
subclassing :class:`n6sdk.data_spec.DataSpec` to create a custom data
specification class -- in which you can:

* add new field specifications as well as modify (extend), replace or
  remove (mask) field specifications defined by
  :class:`~n6sdk.data_spec.DataSpec`;
* extend the :class:`~n6sdk.data_spec.DataSpec`'s cleaning methods.

(See the following sections.)

You may also want to subclass :class:`n6sdk.data_spec.fields.Field`
(or any of its subclasses, such as :class:`~.UnicodeLimitedField`,
:class:`~.IPv4Field` or :class:`~.IntegerField`) to create new kinds
of fields whose instances can be used as field specifications in your
custom data specification class (see below:
:ref:`custom_field_classes`).


.. _data_spec_cleaning_methods:

Data specification cleaning methods
-----------------------------------

The most important methods of any *data specification* (an instance of
:class:`n6sdk.data_spec.DataSpec` or of its subclass) are:

* :meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict` -- used to
  clean client query parameters;

* :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` -- used to
  clean results yielded by the data backend API.

Typically, these methods are called automatically by the *n6sdk*
machinery.

Each of these methods takes *exactly one positional argument* which is
respectively:

* for :meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict` -- a
  **dictionary of query parameters** (representing one client
  request); the dictionary maps query parameter names to their raw
  values (taken directly from the URL query string; a *raw value* can
  consist of several comma-separated *actual values*);

* for :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` -- a
  **single result dictionary** (representing one network incident);
  the dictionary maps result keys to their values.

Each of these methods also accepts the following *optional keyword-only
arguments*:

* `ignored_keys` -- an iterable (e.g., a set or a list) of keys that
  will be completely ignored (i.e., the processed dictionary that has
  been given as the positional argument will be treated as it did not
  contain any of these keys; therefore, the resultant dictionary will
  not contain them either);

* `forbidden_keys` -- an iterable of keys that *must not apperar* in
  the processed dictionary or a validation error (respectively:
  :exc:`.ParamKeyCleaningError` or :exc:`.ResultKeyCleaningError`)
  will be raised;

* `extra_required_keys` -- an iterable of keys that *must appear* in
  the processed dictionary or a validation error (respectively:
  :exc:`.ParamKeyCleaningError` or :exc:`.ResultKeyCleaningError`)
  will be raised;

* `discarded_keys` -- an iterable of keys that will be removed
  (discarded) *after* validation of the processed dictionary keys (and
  *before* cleaning of the processed dictionary values).

Each of these methods returns *a new dictionary* (in other words, the
input dictionary given as the positional argument *is not modified*).
Regarding returned dictionaries:

* a dictionary returned by
  :meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict` maps field
  names (query parameter names) to **lists of cleaned query parameter
  values** (because, as it was said, for most fields there can be more
  than one query parameter value);

* a dictionary returned by
  :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` (containing
  cleaned data of exactly one network incident) maps field names
  (result keys) to **cleaned result values**.


.. _field_cleaning_methods:

Field cleaning methods
----------------------

The most important methods of any *field* (an instance of
:class:`n6sdk.data_spec.fields.Field` or of its subclass) are:

* :meth:`~n6sdk.data_spec.fields.Field.clean_param_value` --
  called to clean a single (*actual*) query parameter value;

* :meth:`~n6sdk.data_spec.fields.Field.clean_result_value` --
  called to clean a single result value.

Each of these methods takes exactly *one positional argument*: a
single uncleaned value.

Each of these methods returns *a single value*: a cleaned one.

These methods are called by the data specification machinery in the
following way:

* The data specification's method
  :meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict` (described
  above in the :ref:`data_spec_cleaning_methods` section), **for each
  actual value extracted from a query parameter's raw value** (a *raw
  value* can consist of several comma-separated *actual values*) **taken
  from the dictionary passed as the argument**, calls the
  :meth:`~n6sdk.data_spec.fields.Field.clean_param_value` method of the
  appropriate field.

  If the field's method raises (or propagates) an exception being an
  instance/subclass of :exc:`~exceptions.Exception` (i.e., practically
  *any* exception, excluding :exc:`~exceptions.KeyboardInterrupt`,
  :exc:`~exceptions.SystemExit` and a few others), the data
  specification's method
  :meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict` catches it
  (and possibly similar exceptions from other fields) and then raises
  :exc:`.ParamValueCleaningError`.

  .. note::

     If the exception raised (or propagated) by the field's method is
     :exc:`.FieldValueError` (or any other exception derived from
     :exc:`._ErrorWithPublicMessageMixin`) its
     :attr:`~._ErrorWithPublicMessageMixin.public_message` will be
     included in the :exc:`.ParamValueCleaningError`'s
     :attr:`~.ParamValueCleaningError.public_message`).

* the data specification's method
  :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` (described
  above in the :ref:`data_spec_cleaning_methods` section) **for each
  value from the dictionary passed as the argument**, calls the
  :meth:`~n6sdk.data_spec.fields.Field.clean_result_value` method of the
  appropriate field.

  If the field's method raises (or propagates) an exception being an
  instance/subclass of :exc:`~exceptions.Exception` (i.e., practically
  *any* exception, excluding :exc:`~exceptions.KeyboardInterrupt`,
  :exc:`~exceptions.SystemExit` and a few others), the data
  specification's method
  :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` catches it
  (and possibly similar exceptions from other fields) and then raises
  :exc:`.ResultValueCleaningError`.

  .. note::

     Unlike :exc:`.ParamValueCleaningError` raised by
     :meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict`, the
     :exc:`.ResultValueCleaningError` exception raised by
     :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` in
     reaction to exception(s) from
     :meth:`~n6sdk.data_spec.fields.Field.clean_result_value` *does
     not* include in its
     :attr:`~.ResultValueCleaningError.public_message` any information
     from the underlying exception(s) (instead of that,
     :exc:`~.ResultValueCleaningError`\ 's
     :attr:`~.ResultValueCleaningError.public_message` is set to the
     safe default: ``u"Internal error."``).

     The rationale for this behaviour is that any exceptions related
     to *result cleaning* are strictly internal (contrary to *query
     parameter cleaning*).

     Thanks to this behaviour, much of the field classes's code
     related to parameter value cleaning could be used also for result
     value cleaning without concern about disclosing some sensitive
     details in :attr:`~.ResultValueCleaningError.public_message` of
     :exc:`~.ResultValueCleaningError`.

     .. warning::

        For security sake, when extending
        :meth:`n6sdk.data_spec.BaseDataSpec.clean_result_dict` ensure
        that your implementation behaves in the same way as described
        in this *note*.


.. _data_spec_overview:

:class:`n6sdk.data_spec.DataSpec` overview
------------------------------------------

The :class:`n6sdk.data_spec.DataSpec` class is a ready-to-use *data
specification class* that performs cleaning of all standard *n6-like*
REST API query parameters and result items.

The following list describes briefly all field specifications defined
by the class:

* ``id``:

  * *in params:* **optional**
  * *in result:* **required**
  * *field class:* :class:`.UnicodeLimitedField`
  * *specific field constructor arguments:* ``max_length=64``
  * *param cleaning example:*

    * *query string item:* ``id=abcDEF,42,x-y-z``
    * *list of cleaned values:* ``[u"abcDEF", u"42", u"x-y-z"]``

  * *result cleaning example:*

    * *raw value:* ``"abcDEF... \xc5\x81"``
    * *cleaned value:* ``u"abcDEF... \u0141"``

  Unique incident identifier being an arbitrary text. Maximum length:
  64 characters (after cleaning).

* ``source``:

  * *in params:* **optional**
  * *in result:* **required**
  * *field class:* :class:`.SourceField`
  * *param cleaning example:*

    * *query string item:* ``source=some-org.some-type,foo.bar``
    * *list of cleaned values:* ``[u"some-org.some-type", u"foo.bar"]``

  * *result cleaning example:*

    * *raw value:* ``"some-org.some-type"``
    * *cleaned value:* ``u"some-org.some-type"``

  Incident data source identifier. Consists of two parts separated
  with a dot (``.``). Allowed characters (apart from the dot) are:
  ASCII lower-case letters, digits and hyphen (``-``). Maximum length:
  32 characters (after cleaning).

* ``restriction``:

  * *in params:* **optional**
  * *in result:* **required**
  * *field class:* :class:`.UnicodeEnumField`
  * *specific field constructor arguments:* ``enum_values=n6sdk.data_spec.RESTRICTION_ENUMS``
  * *param cleaning example:*

    * *query string item:* ``restriction=public``
    * *list of cleaned values:* ``[u"public"]``

  * *result cleaning example:*

    * *raw value:* ``"public"``
    * *cleaned value:* ``u"public"``

  Data distribution restriction qualifier.  One of: ``"public"``,
  ``"need-to-know"`` or ``"internal"``.

* ``confidence``:

  * *in params:* **optional**
  * *in result:* **required**
  * *field class:* :class:`.UnicodeEnumField`
  * *specific field constructor arguments:* ``enum_values=n6sdk.data_spec.CONFIDENCE_ENUMS``
  * *param cleaning example:*

    * *query string item:* ``confidence=medium,low``
    * *list of cleaned values:* ``[u"medium", u"low"]``

  * *result cleaning example:*

    * *raw value:* ``u"medium"``
    * *cleaned value:* ``u"medium"``

  Data confidence qualifier.  One of: ``"high"``, ``"medium"`` or
  ``"low"``.

* ``category``:

  * *in params:* **optional**
  * *in result:* **required**
  * *field class:* :class:`.UnicodeEnumField`
  * *specific field constructor arguments:* ``enum_values=n6sdk.data_spec.CATEGORY_ENUMS``
  * *param cleaning example:*

    * *query string item:* ``category=bots,cnc``
    * *list of cleaned values:* ``[u"bots", u"cnc"]``

  * *result cleaning example:*

    * *raw value:* ``"bots"``
    * *cleaned value:* ``u"bots"``

  Incident category label (some examples: ``"bots"``, ``"phish"``,
  ``"scanning"``...).

* ``time``

  * *in params:* N/A
  * *in result:* **required**
  * *field class:* :class:`.DateTimeField`
  * *result cleaning examples:*

    * *example synonymous raw values:*

      *  ``"2014-11-05T23:13:00.000000"`` or
      *  ``"2014-11-06 01:13+02:00"`` or
      *  ``datetime.datetime(2014, 11, 5, 23, 13, 0)`` or
      *  ``datetime.datetime(2014, 11, 6, 1, 13, 0, 0, <tzinfo with UTC offset 2h>)``

    * *cleaned value:* ``datetime.datetime(2014, 11, 5, 23, 13, 0)``

  Incident *occurrence* time (**not**
  *when-entered-into-the-database*).  Value cleaning includes
  conversion to UTC time.

* ``time.min``:

  * *in params:* **optional, single**
  * *in result:* N/A
  * *field class:* :class:`.DateTimeField`
  * *param cleaning examples:*

    * *example synonymous query string items:*

      * ``time.min=2014-11-06T01:13+02:00`` or
      * ``time.min=2014-11-05 23:13:00.000000``

    * *list of cleaned values:* ``[datetime.datetime(2014, 11, 5, 23, 13, 0)]``

  The *earliest* time the queried incidents *occurred* at.  Value
  cleaning includes conversion to UTC time.

* ``time.max``:

  * *in params:* **optional, single**
  * *in result:* N/A
  * *field class:* :class:`.DateTimeField`
  * *param cleaning examples:*

    * *example synonymous query string items:*

      * ``time.max=2014-11-06T01:13+02:00`` or
      * ``time.max=2014-11-05 23:13:00.000000``

    * *list of cleaned values:* ``[datetime.datetime(2014, 11, 5, 23, 13, 0)]``

  The *latest* time the queried incidents *occurred* at.  Value
  cleaning includes conversion to UTC time.

* ``origin``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.UnicodeEnumField`
  * *specific field constructor arguments:* ``enum_values=n6sdk.data_spec.ORIGIN_ENUMS``
  * *param cleaning example:*

    * *query string item:* ``origin=honeypot``
    * *list of cleaned values:* ``[u"honeypot"]``

  * *result cleaning example:*

    * *raw value:* ``u"honeypot"``
    * *cleaned value:* ``u"honeypot"``

  Incident origin label (some examples: ``"p2p-crawler"``,
  ``"sinkhole"``, ``"honeypot"``...).

* ``name``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.UnicodeLimitedField`
  * *specific field constructor arguments:* ``max_length=255``
  * *param cleaning example:*

    * *query string item:* ``name=LoremIpsuM``
    * *list of cleaned values:* ``[u"LoremIpsuM"]``

  * *result cleaning example:*

    * *raw value:* ``"LoremIpsuM"``
    * *cleaned value:* ``u"LoremIpsuM"``

  Threat's exact name, such as ``"virut"``, ``"Potential SSH Scan"``
  or any other... Maximum length: 255 characters (after cleaning).

* ``target``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.UnicodeLimitedField`
  * *specific field constructor arguments:* ``max_length=100``
  * *param cleaning example:*

    * *query string item:* ``target=LoremIpsuM``
    * *list of cleaned values:* ``[u"LoremIpsuM"]``

  * *result cleaning example:*

    * *raw value:* ``"LoremIpsuM"``
    * *cleaned value:* ``u"LoremIpsuM"``

  Name of phishing target (organization, brand etc.). Maximum length:
  100 characters (after cleaning).

* ``address``

  * *in params:* N/A
  * *in result:* **optional**
  * *field class:* :class:`.AddressField`
  * *result cleaning examples:*

    * *example synonymous raw values:*

      * ``[{"ip": "123.10.234.168"}, {"ip": "123.10.234.169", "asn": 999998}]`` or
      * ``[{u"ip": "123.10.234.168"}, {"ip": "123.10.234.169", u"asn": "999998"}]`` or
      * ``[{"ip": "123.10.234.168"}, {u"ip": "123.10.234.169", u"asn": "15.16958"}]``

    * *cleaned value:* ``[{u"ip": u"123.10.234.168"}, {u"ip": "123.10.234.169", u"asn": 999998}]``

  Set of network addresses related to the returned incident (e.g., for
  malicious web sites: taken from DNS *A* records; for
  sinkhole/scanning: communication source addresses) -- in the form of
  a list of dictionaries, each containing ``"ip"`` (IPv4 address in
  quad-dotted decimal notation, cleaned using a subfield being an
  instance of :class:`.IPv4Field`), and optionally: ``"asn"``
  (autonomous system number in the form of a number or two numbers
  separated with a dot, cleaned using a subfield being an instance of
  :class:`.ASNField`) and/or ``"cc"`` (two-letter country code,
  cleaned using a subfield being an instance of :class:`.CCField`).

* ``ip``:

  * *in params:* **optional**
  * *in result:* N/A
  * *field class:* :class:`.IPv4Field`
  * *param cleaning example:*

    * *query string item:* ``ip=123.10.234.168,123.10.234.169``
    * *list of cleaned values:* ``[u"123.10.234.168", u"123.10.234.169"]``

  IPv4 address (in quad-dotted decimal notation) related to the
  queried incidents.

* ``ip.net``:

  * *in params:* **optional**
  * *in result:* N/A
  * *field class:* :class:`.IPv4NetField`
  * *param cleaning example:*

    * *query string item:* ``ip.net=123.10.234.0/24,12.34.0.0/16``
    * *list of cleaned values:* ``[(u"123.10.234.0", 24), (u"12.34.0.0", 16)]``

  IPv4 network (in CIDR notation) containing IP addresses related to
  the queried incidents.

* ``asn``:

  * *in params:* **optional**
  * *in result:* N/A
  * *field class:* :class:`.ASNField`
  * *param cleaning example:*

    * *query string item:* ``asn=123,999999,15.16958``
    * *list of cleaned values:* ``[123, 999999, 999998]``

  Autonomous system number of IP addresses related to the queried
  incidents; in the form of a number or two numbers separated with a
  dot (see the examples above).

* ``cc``:

  * *in params:* **optional**
  * *in result:* N/A
  * *field class:* :class:`.CCField`
  * *param cleaning example:*

    * *query string item:* ``cc=JP,UA,PL,US``
    * *list of cleaned values:* ``[u"JP", u"UA", u"PL", u"US"]``

  Two-letter country code related to IP addresses related to the
  queried incidents.

.. _field_spec_url:

* ``url``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.URLField`
  * *param cleaning example:*

    * *query string item:* ``url=ftp://example.com/foo,http://x/XYZ``
    * *list of cleaned values:* ``[u"ftp://example.com/foo", u"http://x/XYZ"]``

  * *result cleaning examples:*

    * *example synonymous raw values:*

      * ``"ftp://example.com/non-utf8-\xdd"`` or
      * ``u"ftp://example.com/non-utf8-\udcdd"`` or
      * ``"ftp://example.com/non-utf8-\xed\xb3\x9d"``

    * *cleaned value:* ``u"ftp://example.com/non-utf8-\udcdd"``

  URL related to the queried/returned incidents. Maximum length: 2048
  characters (after cleaning).

  .. note::

     Cleaning involves decoding byte strings using the
     ``surrogateescape`` error handler backported from Python 3.x
     (see: :func:`n6sdk.encoding_helpers.provide_surrogateescape`).

* ``url.sub``:

  * *in params:* **optional**
  * *in result:* N/A
  * *field class:* :class:`.URLSubstringField`
  * *param cleaning example:*

    * *query string item:* ``url.sub=/example.c,XY``
    * *list of cleaned values:* ``[u"/example.c", u"XY"]``

  Substring of URLs related to the queried incidents. Maximum length:
  2048 characters (after cleaning).

  .. seealso::

     The above :ref:`url <field_spec_url>` description.

.. _field_spec_fqdn:

* ``fqdn``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.DomainNameField`
  * *param cleaning example:*

    * *query string item:* ``fqdn=example.com,wwW.ŁÓDKa.Example.ORG``
    * *list of cleaned values:* ``[u"example.com", u"www.xn--dka-fna80b.example.org"]``

  * *result cleaning examples:*

    * *example synonymous raw values:*

      * ``u"WWW.ŁÓDKA.ORG.EXAMPLE"`` or
      * ``"WWW.\xc5\x81\xc3\x93DKA.ORG.EXAMPLE"`` or
      * ``u"wwW.łódka.org.Example"`` or
      * ``"www.\xc5\x82\xc3\xb3dka.org.Example"`` or
      * ``u"www.xn--dka-fna80b.org.example"`` or
      * ``"www.xn--dka-fna80b.example.org"``

    * *cleaned value:* ``u"www.xn--dka-fna80b.example.org"``

  Fully qualified domain name related to the queried/returned
  incidents (e.g., for malicious web sites: from the site's URL; for
  sinkhole/scanning: the domain used for communication). Maximum
  length: 255 characters (after cleaning).

  .. note::

     During cleaning, the ``IDNA`` encoding is applied (see:
     https://docs.python.org/2.7/library/codecs.html#module-encodings.idna
     and http://en.wikipedia.org/wiki/Internationalized_domain_name;
     see also the above examples), then all remaining upper-case
     letters are converted to lower-case.

* ``fqdn.sub``:

  * *in params:* **optional**
  * *in result:* N/A
  * *field class:* :class:`.DomainNameSubstringField`
  * *param cleaning example:*

    * *query string item:* ``fqdn.sub=mple.c,ORG``
    * *list of cleaned values:* ``[u"mple.c", u"org"]``

  Substring of fully qualified domain names related to the queried
  incidents. Maximum length: 255 characters (after cleaning).

  .. seealso::

     The above :ref:`fqdn <field_spec_fqdn>` description.

* ``proto``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.UnicodeEnumField`
  * *specific field constructor arguments:* ``enum_values=n6sdk.data_spec.PROTO_ENUMS``
  * *param cleaning example:*

    * *query string item:* ``proto=tcp,udp``
    * *list of cleaned values:* ``[u"tcp", u"udp"]``

  * *result cleaning example:*

    * *raw value:* ``"tcp"``
    * *cleaned value:* ``u"tcp"``

  Layer #4 protocol label -- one of: ``"tcp"``, ``"udp"``, ``"icmp"``.

* ``sport``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.PortField`
  * *param cleaning example:*

    * *query string item:* ``sport=80,12345``
    * *list of cleaned values:* ``[80, 12345]``

  * *result cleaning examples:*

    * *example synonymous raw values:* ``80`` or ``80.0`` or ``"80"``
    * *cleaned value:* ``80``

  TCP/UDP source port (non-negative integer number, less than 65536).

* ``dport``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.PortField`
  * *param cleaning example:*

    * *query string item:* ``dport=80,12345``
    * *list of cleaned values:* ``[80, 12345]``

  * *result cleaning example:*

    * *example synonymous raw values:* ``80`` or ``80.0`` or ``"80"``
    * *cleaned value:* ``80``

  TCP/UDP destination port (non-negative integer number, less than
  65536).

* ``dip``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.IPv4Field`
  * *param cleaning example:*

    * *query string item:* ``dip=123.10.234.168,123.10.234.169``
    * *list of cleaned values:* ``[u"123.10.234.168", u"123.10.234.169"]``

  * *result cleaning example:*

    * *raw value:* ``"123.10.234.168"``
    * *cleaned value:* ``u"123.10.234.168"``

  Destination IPv4 address (for sinkhole, honeypot etc.; does not
  apply to malicious web sites) in quad-dotted decimal notation.

* ``adip``:

  * *in params:* N/A
  * *in result:* **optional**
  * *field class:* :class:`.AnonymizedIPv4Field`
  * *result cleaning example:*

    * *raw value:* ``"x.X.234.168"``
    * *cleaned value:* ``u"x.x.234.168"``

  Anonymized destination IPv4 address: in quad-dotted decimal
  notation, with one or more segments replaced with ``"x"``, for
  example: ``"x.168.0.1"`` or ``"x.x.x.1"`` (*note:* at least the
  leftmost segment must be replaced with ``"x"``).

* ``md5``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.MD5Field`
  * *param cleaning example:*

    * *query string item:* ``md5=b555773768bc1a672947d7f41f9c247f``
    * *list of cleaned values:* ``[u"b555773768bc1a672947d7f41f9c247f"]``

  * *result cleaning example:*

    * *raw value:* ``"b555773768bc1a672947d7f41f9c247f"``
    * *cleaned value:* ``u"b555773768bc1a672947d7f41f9c247f"``

  MD5 hash of the binary file related to the (queried/returned)
  incident.  In the form of a string of 32 hexadecimal digits.

* ``sha1``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.SHA1Field`
  * *param cleaning example:*

    * *query string item:* ``sha1=7362d67c4f32ba5cd9096dcefc81b28ca04465b1``
    * *list of cleaned values:* ``[u"7362d67c4f32ba5cd9096dcefc81b28ca04465b1"]``

  * *result cleaning example:*

    * *raw value:* ``u"7362d67c4f32ba5cd9096dcefc81b28ca04465b1"``
    * *cleaned value:* ``u"7362d67c4f32ba5cd9096dcefc81b28ca04465b1"``

  SHA1 hash of the binary file related to the (queried/returned)
  incident.  In the form of a string of 40 hexadecimal digits.

* ``expires``:

  * *in params:* N/A
  * *in result:* **optional**
  * *field class:* :class:`.DateTimeField`
  * *result cleaning examples:*

    * *example synonymous raw values:*

      *  ``"2014-11-05T23:13:00.000000"`` or
      *  ``"2014-11-06 01:13+02:00"`` or
      *  ``datetime.datetime(2014, 11, 5, 23, 13, 0)`` or
      *  ``datetime.datetime(2014, 11, 6, 1, 13, 0, 0, <tzinfo with UTC offset 2h>)``

    * *cleaned value:* ``datetime.datetime(2014, 11, 5, 23, 13, 0)``

  Black list item *expiry* time.  Value cleaning includes conversion
  to UTC time.

* ``active.min``:

  * *in params:* **optional, single**
  * *in result:* N/A
  * *field class:* :class:`.DateTimeField`
  * *param cleaning examples:*

    * *example synonymous query string items:*

      * ``active.min=2014-11-05T23:13:00.000000`` or
      * ``active.min=2014-11-06 01:13+02:00``

    * *list of cleaned values:* ``[datetime.datetime(2014, 11, 5, 23, 13, 0)]``

  The *earliest* expiry-or-occurrence time of the queried black list
  items.  Value cleaning includes conversion to UTC time.

* ``active.max``:

  * *in params:* **optional, single**
  * *in result:* N/A
  * *field class:* :class:`.DateTimeField`
  * *param cleaning examples:*

    * *example synonymous query string items:*

      * ``active.max=2014-11-05T23:13:00.000000`` or
      * ``active.max=2014-11-06 01:13+02:00``

    * *list of cleaned values:* ``[datetime.datetime(2014, 11, 5, 23, 13, 0)]``

  The *latest* expiry-or-occurrence time of the queried black list
  items.  Value cleaning includes conversion to UTC time.

* ``status``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.UnicodeEnumField`
  * *specific field constructor arguments:* ``enum_values=n6sdk.data_spec.STATUS_ENUMS``
  * *param cleaning example:*

    * *query string item:* ``status=active,replaced``
    * *list of cleaned values:* ``[u"active", u"replaced"]``

  * *result cleaning example:*

    * *raw value:* ``"active"``
    * *cleaned value:* ``u"active"``

  Black list item status qualifier.  One of: ``"active"`` (item
  currently in the list), ``"delisted"`` (item removed from the list),
  ``"expired"`` (item expired, so treated as removed by the n6 system)
  or ``"replaced"`` (e.g.: IP address changed for the same URL).

* ``replaces``:

  * *in params:* **optional**
  * *in result:* **optional**
  * *field class:* :class:`.UnicodeLimitedField`
  * *specific field constructor arguments:* ``max_length=64``
  * *param cleaning example:*

    * *query string item:* ``replaces=abcDEF``
    * *list of cleaned values:* ``[u"abcDEF"]``

  * *result cleaning example:*

    * *raw value:* ``"abcDEF"``
    * *cleaned value:* ``u"abcDEF"``

  ``id`` of the black list item replaced by the queried/returned one.

* ``until``:

  * *in params:* N/A
  * *in result:* **optional**
  * *field class:* :class:`.DateTimeField`
  * *result cleaning examples:*

    * *example synonymous raw values:*

      *  ``"2014-11-05T23:13:00.000000"`` or
      *  ``"2014-11-06 01:13+02:00"`` or
      *  ``datetime.datetime(2014, 11, 5, 23, 13, 0)`` or
      *  ``datetime.datetime(2014, 11, 6, 1, 13, 0, 0, <tzinfo with UTC offset 2h>)``

    * *cleaned value:* ``datetime.datetime(2014, 11, 5, 23, 13, 0)``

  For *aggregated events*: the occurrence time of the *latest*
  [newest] aggregated event represented by the returned incident data
  record (*note:* ``time`` is the occurrence time of the *first*
  [oldest] aggregated event).  Value cleaning includes conversion to
  UTC time.

* ``count``:

  * *in params:* N/A
  * *in result:* **optional**
  * *field class:* :class:`.IntegerField`
  * *specific field constructor arguments:* ``min_value=0, max_value=32767``
  * *result cleaning examples:*

    * *example synonymous raw values:* ``42`` or ``42.0`` or ``"42"``
    * *cleaned value:* ``42``

  For *aggregated events*: number of events represented by the
  returned incident data record.  It must be a positive integer number
  not greater than 32767.

.. note::

   **Generally**, byte strings (if any), when converted to Unicode
   strings, are by default decoded using the ``utf-8`` encoding.


.. _extending_data_spec:

Subclassing :class:`n6sdk.data_spec.DataSpec`
---------------------------------------------

You can create your own *data specification class* by subclassing
:class:`n6sdk.data_spec.DataSpec`.

Let us **prepare a separate module for our custom data
specification**:

.. code-block:: bash

   $ cd <the main directory of the project>/using_n6sdk
   $ touch data_spec.py

Then, we can open the newly created file (``data_spec.py``) with our
favorite text editor and **place the following code in it**::

    from n6sdk.data_spec import DataSpec
    from n6sdk.data_spec.fields import UnicodeRegexField

    class CustomDataSpec(DataSpec):

        mac_address = UnicodeRegexField(
            in_params='optional',  # *can* be in query params
            in_result='optional',  # *can* be in result data

            regex=r'^(?:[0-9A-F]{2}(?:[:-]|$)){6}$',
            error_msg_template=u'"{}" is not a valid MAC address',
        )

We just made a new *data specification class* -- very similar to
:class:`~n6sdk.data_spec.DataSpec` but with one additional field
specification: ``mac_address``.

We could also modify (extend) within our subclass some of the field
specifications inherited from :class:`~n6sdk.data_spec.DataSpec`.  For
example::

    from n6sdk.data_spec import (
        DataSpec,
        Ext,
    )

    class CustomDataSpec(DataSpec):
        # ...

        id = Ext(
            # here: changing the `max_length` property
            # of the `id` field -- from 64 to 32
            max_length=32,
        )
        time = Ext(
            # here: enabling bare `time` also for queries
            # (by default `time.min` and `time.max` query
            # params are allowed but bare `time` is not)
            in_params='optional',

            # here: making `time.max` a required (obligatory,
            # not optional) query parameter
            extra_params=Ext(
                max=Ext(in_params='required'),
            ),
        )

Please note how :class:`n6sdk.data_spec.Ext` is used above to extend
existing (inherited) field specifications.

It is also possible to replace existing (inherited) field
specifications with completely new definitions...

::

    # ...
    from n6sdk.data_spec.fields import MD5Field
    # ...

    class CustomDataSpec(DataSpec):
        # ...
        id = MD5Field(
            in_params='optional',
            in_result='required',
        )
        # ...

...as well as to remove (mask) them::

    # ...
    class CustomDataSpec(DataSpec):
        # ...
        count = None


You can also extend the
:meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict` and
:meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` methods::

    # ...

    def _is_april_fools_day():
        now = datetime.datetime.utcnow()
        return now.month == 4 and now.day == 1


    class CustomDataSpec(DataSpec):

        def clean_param_dict(self, params, ignored_keys=(), **kwargs):
            if _is_april_fools_day():
                ignored_keys = set(ignored_keys) | {'joke'}
            return super(CustomDataSpec, self).clean_param_dict(
                params,
                ignored_keys=ignored_keys,
                **kwargs)

        def clean_result_dict(self, result, **kwargs):
            if _is_april_fools_day():
                result['time'] = '1810-03-01T13:13'
            return super(CustomDataSpec, self).clean_result_dict(
                result,
                **kwargs)


.. note::

   Manipulating the optional keyword-only arguments (`ignored_keys`,
   `forbidden_keys`, `extra_required_keys`, `discarded_keys` -- see
   above: :ref:`data_spec_cleaning_methods`) of these methods can be
   useful, for example, when you need to implement some
   authentication-driven data anonymization or
   param/result-key-focused access rules (however, in such a case you
   may also need to add some additional keyword-only arguments to the
   signatures of these methods, e.g. `auth_data`; then you will also
   need to extend the :meth:`~.get_clean_param_dict_kwargs` and/or
   :meth:`~.get_clean_result_dict_kwargs` methods of your custom
   subclass of :class:`~.DefaultStreamViewBase`; generally that matter
   is beyond the scope of this tutorial).


.. _n6sdk_field_classes:

Standard *n6sdk* field classes
------------------------------

The following list briefly describes all field classes defined in the
:mod:`n6sdk.data_spec.fields` module:

* :class:`~.Field`:

  The top-level base class for field specifications.

* :class:`~.DateTimeField`:

  * *raw (uncleaned) result value type:* :class:`str`/:class:`unicode`
    or :class:`datetime.datetime`
  * *cleaned value type:* :class:`datetime.datetime`
  * *example cleaned value:* ``datetime.datetime(2014, 11, 6, 13, 30, 1)``

  For date-and-time (timestamp) values, automatically normalized to
  UTC.

* :class:`~.UnicodeField`:

  * *base classes:* :class:`~.Field`
  * *most useful constructor arguments or subclass attributes:*

    * **encoding** (default: ``"utf-8"``)
    * **decode_error_handling** (default: ``"strict"``)

  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"Some text value. Zażółć gęślą jaźń."``

  For arbitrary text data.

* :class:`~.HexDigestField`:

  * *base classes:* :class:`~.UnicodeField`
  * **obligatory** *constructor arguments or subclass attributes:*

    * **num_of_characters** (exact number of characters)
    * **hash_algo_descr** (hash algorithm label, such as ``"MD5"`` or
      ``"SHA256"``...)

  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`

  For hexadecimal digests (hashes), such as *MD5*, *SHA256* or any
  other...

* :class:`~.MD5Field`:

  * *base classes:* :class:`~.HexDigestField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"b555773768bc1a672947d7f41f9c247f"``

  For hexadecimal MD5 digests (hashes).

* :class:`~.SHA1Field`:

  * *base classes:* :class:`~.HexDigestField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"7362d67c4f32ba5cd9096dcefc81b28ca04465b1"``

  For hexadecimal SHA1 digests (hashes).

* :class:`~.UnicodeEnumField`:

  * *base classes:* :class:`~.UnicodeField`
  * **obligatory** *constructor arguments or subclass attributes:*

    * **enum_values** (a sequence or set of strings)

  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"Some selected text value"``

  For text data limited to a finite set of possible values.

* :class:`~.UnicodeLimitedField`:

  * *base classes:* :class:`~.UnicodeField`
  * **obligatory** *constructor arguments or subclass attributes:*

    * **max_length** (maximum number of characters)

  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"Some not-too-long text value"``

  For text data with limited length.

* :class:`~.UnicodeRegexField`:

  * *base classes:* :class:`~.UnicodeField`
  * **obligatory** *constructor arguments or subclass attributes:*

    * **regex** (regular expression -- as a string or compiled regular
      expression object)

  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"Some matching text value"``

  For text data limited by the specified regular expression.

* :class:`~.SourceField`:

  * *base classes:* :class:`~.UnicodeLimitedField`, :class:`~.UnicodeRegexField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"some-organization.some-type"``

  For dot-separated source specifications, such as ``organization.type``.

* :class:`~.IPv4Field`:

  * *base classes:* :class:`~.UnicodeLimitedField`, :class:`~.UnicodeRegexField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"123.10.234.168"``

  For IPv4 addresses (in decimal dotted-quad notation).

* :class:`~.AnonymizedIPv4Field`:

  * *base classes:* :class:`~.UnicodeLimitedField`, :class:`~.UnicodeRegexField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"x.10.234.168"``

  For anonymized IPv4 addresses (in decimal dotted-quad notation, with
  the leftmost octet -- and possibly any other octets -- replaced
  with ``"x"``).

* :class:`~.IPv4NetField`:

  * *base classes:* :class:`~.UnicodeLimitedField`, :class:`~.UnicodeRegexField`
  * *raw (uncleaned) result value type:* :class:`str`/:class:`unicode`
    or 2-:class:`tuple`: ``(<str/unicode>, <int>)``
  * *cleaned value types:*

    * **of cleaned param values:** 2-:class:`tuple`: ``(<unicode>, <int>)``
    * **of cleaned result values:** :class:`unicode`

  * *example cleaned values:*

    * **cleaned param value:** ``(u"123.10.0.0", 16)``
    * **cleaned result value:** ``u"123.10.0.0/16"``

  For IPv4 network specifications (in CIDR notation).

* :class:`~.CCField`:

  * *base classes:* :class:`~.UnicodeLimitedField`, :class:`~.UnicodeRegexField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"JP"``

  For 2-letter country codes.

* :class:`~.URLSubstringField`:

  * *base classes:* :class:`~.UnicodeLimitedField`
  * *most useful constructor arguments or subclass attributes:*

    * **decode_error_handling** (default: ``'surrogateescape'``)

  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"/xyz.example.c"``

  For substrings of URLs.

* :class:`~.URLField`:

  * *base classes:* :class:`~.URLSubstringField`
  * *most useful constructor arguments or subclass attributes:*

    * **decode_error_handling** (default: ``'surrogateescape'``)

  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"http://xyz.example.com/path?query=foo#bar"``

  For URLs.

* :class:`~.DomainNameSubstringField`:

  * *base classes:* :class:`~.UnicodeLimitedField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"xample.or"``

  For substrings of domain names, automatically IDNA-encoded and
  lower-cased.

* :class:`~.DomainNameField`:

  * *base classes:* :class:`~.DomainNameSubstringField`, :class:`~.UnicodeRegexField`
  * *raw (uncleaned) result value type:* :class:`str` or :class:`unicode`
  * *cleaned value type:* :class:`unicode`
  * *example cleaned value:* ``u"www.xn--w-uga1v8h.example.org"``

  For domain names, automatically IDNA-encoded and lower-cased.

* :class:`~.IntegerField`:

  * *base classes:* :class:`~.Field`
  * *most useful constructor arguments or subclass attributes:*

    * **min_value** (*optional* minimum value)
    * **max_value** (*optional* maximum value)

  * *raw (uncleaned) result value type:* :class:`str`/:class:`unicode`
    or an **integer number** of *any numeric type*
  * *cleaned value type:* :class:`int` or (for bigger numbers) :class:`long`
  * *example cleaned value:* ``42``

  For integer numbers (optionally with minimum/maximum limits
  defined).

* :class:`~.ASNField`:

  * *base classes:* :class:`~.IntegerField`
  * *raw (uncleaned) result value type:* :class:`str`/:class:`unicode`
    or :class:`int`/:class:`long`
  * *cleaned value type:* :class:`int` or (possibly, for bigger numbers) :class:`long`
  * *example cleaned value:* ``123456789``

  For autonomous system numbers, such as ``12345``, ``123456789`` or
  ``12345.65432``.

* :class:`~.PortField`:

  * *base classes:* :class:`~.IntegerField`
  * *raw (uncleaned) result value type:* :class:`str`/:class:`unicode`
    or an **integer number** of *any numeric type*
  * *cleaned value type:* :class:`int`
  * *example cleaned value:* ``12345``

  For TCP/UDP port numbers.

* :class:`~.ResultListFieldMixin`:

  * *base classes:* :class:`~.Field`
  * *most useful constructor arguments or subclass attributes:*

    * **allow_empty** (default: ``False`` which means that an empty
      sequence causes a cleaning error)

  A mix-in class for fields whose result values are supposed to be a
  *sequence of values* and not single values.  Its
  :meth:`~.ResultListFieldMixin.clean_result_value` checks that its
  argument is a *non-string sequence* (:class:`list` or
  :class:`tuple`, or any other :class:`collections.Sequence` not being
  :class:`str` or :class:`unicode`) and performs result cleaning (as
  defined in a superclass) for *each item* of it.  See: the
  :ref:`AddressField <field_class_AddressField>` description below.

* :class:`~.DictResultField`:

  * *base classes:* :class:`~.Field`
  * **obligatory** *constructor arguments or subclass attributes:*

    * **key_to_subfield_factory** (a dictionary that maps subfield
      names to field classes or field factory functions)

  * *other useful constructor arguments or subclass attributes:*

    * **required_keys** (a set of keys that *must* appear in a
      dictionary being a cleaned value or a cleaning error is
      raised; default: empty :class:`frozenset`)

  * *raw (uncleaned) result value type:* :class:`collections.Mapping`
  * *cleaned value type:* :class:`dict`

  A base class for fields whose result values are supposed to be
  dictionaries (whose fixed structure is defined by the
  *key_to_subfield_factory* and *required_keys* properties, described
  above).

  .. note::

     This is a result-only field class, i.e. its
     :meth:`~.DictResultField.clean_param_value` raises
     :exc:`~.exceptions.NotImplementedError`.

.. _field_class_AddressField:

* :class:`~.AddressField`:

  * *base classes:* :class:`~.ResultListFieldMixin`,
    :class:`~.DictResultField`
  * *raw (uncleaned) result value type:* :class:`collections.Sequence`
    of :class:`collections.Mapping` instances
  * *cleaned value type:* :class:`list` of :class:`dict` instances
  * *example cleaned values:*

    * **cleaned param value:** N/A
      (:meth:`~.DictResultField.clean_param_value` raises
      :exc:`~.exceptions.NotImplementedError`)
    * **cleaned result value:** ``[{u"ip": u"123.10.234.169", u"cc":
      u"UA", u"asn": 12345}]``

  For lists of dictionaries containing ``"ip"`` and optionally
  ``"cc"`` and/or ``"asn"``.


.. note::

   **Generally --**

   * constructor arguments, when specified, must be provided as
     *keyword arguments*;
   * "constructor argument or a subclass attribute" means that a
     certain field property can be specified in two alternative ways:
     either when instantiating the field (as a keyword argument for
     the constructor) or when subclassing the field (as an attribute
     of a subclass; see below: :ref:`custom_field_classes`);
   * raw (uncleaned) *parameter* value type is *always*
     :class:`str`/:class:`unicode`;
   * all these classes are *cooperative-inheritance*-friendly (i.e.,
     :func:`super` in subclasses' :meth:`clean_param_value` and
     :meth:`clean_result_value` will work properly, also for multiple
     inheritance).


.. seealso::

   The :ref:`data_spec_overview` section above.


.. _custom_field_classes:

Custom field classes
--------------------

You may want to subclass any of the *n6sdk* field classes (described
above in the :ref:`n6sdk_field_classes` section):

* to override class attributes,

* to extend the
  :meth:`~n6sdk.data_spec.fields.Field.clean_param_value` and/or
  :meth:`~n6sdk.data_spec.fields.Field.clean_result_value` method.

Please, consider the example from one of the previous sections::

    from n6sdk.data_spec import DataSpec

    class CustomDataSpec(DataSpec):

        mac_address = UnicodeRegexField(
            in_params='optional',  # *can* be in query params
            in_result='optional',  # *can* be in result data

            regex=r'^(?:[0-9A-F]{2}(?:[:-]|$)){6}$',
            error_msg_template=u'"{}" is not a valid MAC address',
        )

It can be rewritten in a more self-documenting and
code-reusability-friendly way::

    from n6sdk.data_spec import DataSpec
    from n6sdk.data_spec.fields import UnicodeRegexField


    class MacAddressField(UnicodeRegexField):

        regex = r'^(?:[0-9A-F]{2}(?:[:-]|$)){6}$'
        error_msg_template = u'"{}" is not a valid MAC address'


    class CustomDataSpec(DataSpec):

        mac_address = MacAddressField(
            in_params='optional',  # *can* be in query params
            in_result='optional',  # *can* be in result data
        )

**Let us save the above code replacing the contents of the**
``data_spec.py`` **file we created earlier** (see:
:ref:`extending_data_spec`).

Another technique -- extending the value cleaning methods (see above:
:ref:`field_cleaning_methods`) -- offers more possibilities.  Let us
try to create an integer number field that accepts parameter values
with such suffixes as ``"m"`` (*meters*), ``"kg"`` (*kilograms*) and
``"s"`` (*seconds*), ignoring the suffixes::

    from n6sdk.data_spec.fields import IntegerField

    class SuffixedIntegerField(IntegerField):

        # the `legal_suffixes` class attribute we create here
        # can be overridden with a `legal_suffixes` constructor
        # argument or a `legal_suffixes` subclass attribute
        legal_suffixes = 'm', 'kg', 's'

        def clean_param_value(self, value):
            """
            >>> SuffixedIntegerField().clean_param_value('123 kg')
            123
            """
            value = value.strip()
            for suffix in self.legal_suffixes:
                if value.endswith(suffix):
                    value = value[:(-len(suffix))]
                    break
            value = super(SuffixedIntegerField,
                          self).clean_param_value(value)
            return value

If -- in your implementation of
:meth:`~n6sdk.data_spec.fields.Field.clean_param_value` or
:meth:`~n6sdk.data_spec.fields.Field.clean_result_value` -- you need
to raise a cleaning error (to signal that a value is invalid and
cannot be cleaned) just raise any exception being an instance/subclass
of standard Python :exc:`~exceptions.Exception`; it *can* (but *does
not have to*) be :exc:`n6sdk.exceptions.FieldValueError`.

When subclassing *n6sdk* field classes, please do not be afraid to
look into the source code of the :mod:`n6sdk.data_spec.fields` module.


.. _data_backend_api:

Implementing the data backend API
=================================

.. _data_backend_api_interface:

The interface
-------------

The network incident data can be stored in various ways: using text
files, in an SQL database, using some distributed storage such as
Hadoop etc.  Implementation of obtaining data from any of such
backends is beyond the scope of this document.  What we do concern
here is the API the *n6sdk*'s machinery needs to use to get the data.

Therefore, for the purposes of this tutorial, we will assume that our
network incident data is stored in the simplest possible way: *in one
file in the JSON format*.  You will have to replace any implementation
details related to this particular way of keeping and querying for
data with an implementation appropriate for the data store you use
(file reads, SQL queries or whatever is needed for the particular
storage backend) -- see the next section:
:ref:`implementation_guidelines`.

First, we will **create the example JSON data file**:

.. code-block:: bash

   $ cat << EOF > /tmp/our-data.json
        [
          {
            "id": "1", 
            "address": [
              {
                "ip": "11.22.33.44"
              }, 
              {
                "asn": 12345, 
                "cc": "US", 
                "ip": "123.124.125.126"
              }
            ], 
            "category": "phish", 
            "confidence": "low", 
            "mac_address": "00:11:22:33:44:55", 
            "restriction": "public", 
            "source": "test.first", 
            "time": "2014-04-01 10:00:00", 
            "url": "http://example.com/?spam=ham"
          }, 
          {
            "id": "2", 
            "adip": "x.2.3.4", 
            "category": "server-exploit", 
            "confidence": "medium", 
            "restriction": "need-to-know", 
            "source": "test.first", 
            "time": "2014-04-01 23:59:59"
          }, 
          {
            "id": "3", 
            "address": [
              {
                "ip": "11.22.33.44"
              }, 
              {
                "asn": 87654321, 
                "cc": "PL", 
                "ip": "111.122.133.144"
              }
            ], 
            "category": "server-exploit", 
            "confidence": "high", 
            "restriction": "public", 
            "source": "test.second", 
            "time": "2014-04-01 23:59:59", 
            "url": "http://example.com/?spam=ham"
          }
        ]
   EOF

Then, we need to **create the Python module for our data backend API
class**:

.. code-block:: bash

   $ cd <the main directory of the project>/using_n6sdk
   $ touch data_backend_api.py

Now we can open the newly created file (``data_backend_api.py``) with
our favorite text editor and **place the following code in it**::

    import json

    from n6sdk.class_helpers import singleton
    from n6sdk.exceptions import AuthorizationError


    @singleton
    class DataBackendAPI(object):

        def __init__(self, settings):
            # STORAGE-SPECIFIC IMPLEMENTATION DETAILS:
            # (for our example JSON-file-based storage...)
            with open(settings['json_data_file_path']) as f:
                self.data = json.load(f)

        # one or more data query methods (they can have any names):

        def generate_incidents(self, auth_data, params):
            # STORAGE-SPECIFIC IMPLEMENTATION DETAILS:
            # (this is a naive implementation; in a real one some
            # efficient database query needs to be performed here...)
            for incident in self.data:
                for key, value_list in params.items():
                    if key in ('ip', 'asn', 'cc'):
                        address_seq = incident.get('address', [])
                        if not any(addr.get(key) in value_list
                                   for addr in address_seq):
                            break   # incident does not match the query params
                    # WARNING: *.min/*.max/*.sub/ip.net queries are
                    # not supported by this simplified implementation
                    elif incident.get(key) not in value_list:
                        break       # incident does not match the query params
                else:
                    yield incident  # incident matches the query params

What is important:

1. The constructor of the class is supposed to be called exactly once
   per application run. The constructor must take exactly one
   argument:

   * `settings` -- a dictionary containing settings from the ``*.ini``
     file (e.g., ``development.ini`` or ``production.ini``).

2. The class can have one or more data query methods, with arbitrary
   names (in the above example there is only one:
   :func:`generate_incidents`; to learn how URLs are mapped to
   particular data query method names -- see below:
   :ref:`gluing_it_together`).

   Each data query method must take two positional arguments:

   * `auth_data` -- authentication data, relevant only if you need to
     implement in your data query methods some kind of authorization
     based on the authentication data; its type and format depends on
     the authentication policy you use (see below:
     :ref:`custom_authn_policy`);
   * `params` -- a dictionary containing cleaned (validated and
     normalized with
     :meth:`~n6sdk.data_spec.BaseDataSpec.clean_param_dict`) client
     query parameters; the dictionary maps parameter names (strings)
     to lists of parameter values (see above: :ref:`data_spec_class`).

3. Each data query method must be a *generator* (see:
   https://docs.python.org/2/glossary.html#term-generator) or any
   other callable provided that it returns an *iterator* (see:
   https://docs.python.org/2/glossary.html#term-iterator). Each of the
   generated items should be a dictionary containing the data of one
   network incident (the *n6sdk* machinery will use it as the argument
   for the :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict`
   data specification method).


.. _implementation_guidelines:

Guidelines for the real implementation
--------------------------------------

Typically, the following activities are performed **in the __init__()
method** of the data backend API class:

1. Get the storage backend settings from the `settings` dictionary
   (apropriate items should have been placed in the ``[app:main]``
   section of the ``*.ini`` file -- see below:
   :ref:`gluing_it_together`).

2. Configure the storage backend (e.g., create the database
   connection).

Typically, the following activities are performed **in a data query
method** of the data backend API class:

1. If needed: do any authorization checks based on the `auth_data` and
   `params` arguments; raise
   :exc:`n6sdk.exceptions.AuthorizationError` on failure.

2. Translate the contents of the `params` argument to some
   storage-specific queries. (Obviously, when doing the translation
   you may need, for example, to map `params` keys to some
   storage-specific keys...).

   .. note::

      If the data specification includes dotted "extra params" (such
      as ``time.min``, ``time.max``, ``fqdn.sub``, ``ip.net`` etc.)
      their semantics should be implemented carefully.

3. If needed: perform a necessary storage-specific maintenance
   activity (e.g., re-new a database connection if necessary).

4. Perform a storage-specific query (or queries).

   Sometimes you may want to limit the number of allowed results --
   then, if the limit is exceeded you raise
   :exc:`n6sdk.exceptions.TooMuchDataError`.

5. Translate the results of the storage-specific query (queries) to
   result dictionaries and *yield* each of these dictionaries (each of
   them should be a dictionary ready to be passed to the
   :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` method
   defined in your data specification class).

   (Obviously, when doing the translation you may need, for example,
   to map some storage-specific keys to the result keys accepted by
   the :meth:`~n6sdk.data_spec.BaseDataSpec.clean_result_dict` method
   of your data specificaton class...)

   If there are no results -- just do not yield any items (the caller
   will obtain an empty iterator).

6. In case of any internal error, raise
   :exc:`n6sdk.exceptions.DataAPIError`.  If it is caused by another
   exception (that you have caught) it may be good idea to instantiate
   :exc:`~n6sdk.exceptions.DataAPIError` with the result of
   :func:`traceback.format_exc` call as an argument (for debugging
   purposes).

It is recommended to decorate your data backend API class with the
:func:`n6sdk.class_helpers.singleton` decorator (as shown in the
example in the :ref:`data_backend_api_interface` section).


.. _custom_authn_policy:

Custom authentication policy
============================

A description of the concept of *Pyramid authentication policies* is
beyond the scope of this tutorial.  Please read the appropriate
paragraph and example from the documentation of the *Pyramid* library:
http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html#creating-your-own-authentication-policy
(you may also want to search the *Pyramid* documentation for the term
``authentication policy``).

The *n6sdk* library requires that the authentication policy class has
the additional static (decorated with :func:`staticmethod`) method
:meth:`get_auth_data` that takes exactly one positional argument: a
*Pyramid request* object.  The method is expected to return a value
that is **not** :obj:`None` in case of authentication success, and
:obj:`None` otherwise.  Apart from this simple rule there are no
constraints what exactly the return value should be -- the implementer
decides about that.  The return value will be available as the
:obj:`auth_data` attribute of the *Pyramid request* as well as is
passed into data backend API methods as the `auth_data` argument.

Typically, the :meth:`authenticated_userid` method implementation
makes use of the :obj:`auth_data` *request* attribute (being return
value of :meth:`get_auth_data`), and the :meth:`get_auth_data`
implementation makes some use of the :obj:`unauthenticated_userid`
*request* attribute (being return value of the
:meth:`unauthenticated_userid` policy method).  It is possible because
:meth:`get_auth_data` is called (by the *Pyramid* machinery) *after*
the :meth:`unauthenticated_userid` method and *before* the
:meth:`authenticated_userid` method.

The *n6sdk* library provides
:class:`n6sdk.pyramid_commons.BaseAuthenticationPolicy` -- an
authentication policy base class that makes it easier to implement
your own authentication policies. Please consult its source code.


.. _gluing_it_together:

Gluing it together
==================

We will open the ``__init__.py`` file of our application (``<the main
directory of the project>/using_n6sdk/__init__.py``) with our favorite
text editor and **place the following code in it**::

    from n6sdk.pyramid_commons import (
        AnonymousAuthenticationPolicy,
        ConfigHelper,
        HttpResource,
    )

    from using_n6sdk.data_backend_api import DataBackendAPI
    from using_n6sdk.data_spec import CustomDataSpec


    custom_data_spec = CustomDataSpec()

    RESOURCES = [
        HttpResource(
            resource_id='/incidents',
            url_pattern='/incidents.{renderer}',
            renderers=('json', 'sjson'),

            # an *instance* of our data specification class
            data_spec=custom_data_spec,

            # the *name* of a DataBackendAPI's data query method
            data_backend_api_method='generate_incidents',
        ),
    ]


    def main(global_config, **settings):
        helper = ConfigHelper(
            # a dict of settings from the *.ini file
            settings=settings,

            # a data backend API *class*
            data_backend_api_class=DataBackendAPI,

            # an *instance* of an authentication policy class
            authentication_policy=AnonymousAuthenticationPolicy(),

            # the list of HTTP resources defined above
            resources=RESOURCES,
        )
        return helper.make_wsgi_app()

You may also need to **customize the settings** in the ``<the main
directory of the project>/*.ini`` files (``development.ini`` and
``production.ini``), to match your environment, database configuration
(if any) etc.

In case of our naive JSON-file-based data backend implementation (see
above: :ref:`data_backend_api_interface`) we need to **add the
following line in the** ``[app:main]`` **section of each of these two
files**:

.. code-block:: ini

   json_data_file_path = /tmp/our-data.json

Finally, let us run the application (still in the development
environment):

.. code-block:: bash

   $ cd <the main directory of the project>
   $ source dev-venv/bin/activate   # ensuring the virtualenv is active
   $ pserve development.ini

Our application should be being served now.  Try visiting the
following URLs (with any web browser or, for example, with the
``wget`` command-line tool):

* ``http://127.0.0.1:6543/incidents.json``
* ``http://127.0.0.1:6543/incidents.json?ip=11.22.33.44``
* ``http://127.0.0.1:6543/incidents.json?category=phish``
* ``http://127.0.0.1:6543/incidents.json?category=server-exploit``
* ``http://127.0.0.1:6543/incidents.json?category=server-exploit&ip=11.22.33.44``
* ``http://127.0.0.1:6543/incidents.json?category=bots,dos-attacker,phish,server-exploit``
* ``http://127.0.0.1:6543/incidents.sjson?mac_address=00:11:22:33:44:55``
* ``http://127.0.0.1:6543/incidents.sjson?source=test.first``
* ``http://127.0.0.1:6543/incidents.sjson?source=test.second``
* ``http://127.0.0.1:6543/incidents.sjson?source=some.non-existent``

...as well as those causing (expected) errors:

* ``http://127.0.0.1:6543/incidents``
* ``http://127.0.0.1:6543/incidents.json?some-illegal-key=1&another-one=foo``
* ``http://127.0.0.1:6543/incidents.json?category=bots&category=dos-attacker``
* ``http://127.0.0.1:6543/incidents.json?category=wrong``
* ``http://127.0.0.1:6543/incidents.json?category=bots,dos-attacker,wrong``
* ``http://127.0.0.1:6543/incidents.json?ip=11.22.33.44.55``
* ``http://127.0.0.1:6543/incidents.sjson?ip=11.22.33.444``
* ``http://127.0.0.1:6543/incidents.sjson?mac_address=00:11:123456:33:44:55``
* ``http://127.0.0.1:6543/incidents.sjson?time.min=blablabla``


Installation for production (using Apache server)
=================================================

Prerequisites are similar to those concerning the development
environment, listed near the beginning of this tutorial
(:ref:`setting_up_working_env`).  The Debian GNU/Linux operating
system in the version 7.7 or newer is recommended to follow the guides
presented below.  Additional prerequisite is that the Apache2 HTTP
server is installed and configured together with ``mod_wsgi`` (the
``apache2`` and ``libapache2-mod-wsgi`` Debian packages).

First, we will create a directory structure and a *virtualenv* for our
server, e.g. under ``/opt``:

.. code-block:: bash

   $ sudo mkdir /opt/myn6-srv
   $ cd /opt/myn6-srv
   $ sudo virtualenv prod-venv
   $ sudo chown -R $(echo $USER) prod-venv
   $ source prod-venv/bin/activate

Then, let us install the necessary packages:

.. code-block:: bash

   $ cd <the main N6SDK source directory>
   $ python setup.py install
   $ cd <the main directory of the project>
   $ python setup.py install

(Of course, ``<the main n6sdk source directory>`` needs to be replaced
with the actual name (absolute path) of the directory containing the
source code of the *n6sdk* library; and ``<the main directory of the
project>`` needs to be replaced with the actual name (absolute path)
of the directory containing the source code of our *n6sdk*-based
project.)

Now, we will copy the template of the configuration file for
production:

.. code-block:: bash

    $ cd /opt/myn6-srv
    $ sudo cp <the main directory of the project>/production.ini ./

You may want to customize the settings it contains, especially to
match your production environment, database configuration etc.  Just
edit the ``/opt/myn6-srv/production.ini`` file.

Then, we will create the WSGI script:

.. code-block:: bash

    $ cat << EOF > prod-venv/myn6-app.wsgi
    from pyramid.paster import get_app, setup_logging
    ini_path = '/opt/myn6-srv/production.ini'
    setup_logging(ini_path)
    application = get_app(ini_path, 'main')
    EOF

It is also good idea to provide a *Python egg cache*:

.. code-block:: bash

    $ sudo mkdir /opt/myn6-srv/.python-eggs

We need to ensure that the Apache's user has write access to it.  On
Debian GNU/Linux it can be done by executing:

.. code-block:: bash

    $ sudo chown www-data /opt/myn6-srv/.python-eggs

Now, we need to adjust the Apache configuration.  On Debian GNU/Linux
it can be done by executing:

.. code-block:: bash

    $ cat << EOF > prod-venv/myn6.apache
    <VirtualHost *:80>
      # Only one Python sub-interpreter should be used
      # (multiple ones do not cooperate well with C extensions).
      WSGIApplicationGroup %{GLOBAL}

      # Remove the following line if you use native Apache authorisation.
      WSGIPassAuthorization On

      WSGIDaemonProcess myn6_srv \\
        python-path=/opt/myn6-srv/prod-venv/lib/python2.7/site-packages \\
        python-eggs=/opt/myn6-srv/.python-eggs
      WSGIScriptAlias /myn6 /opt/myn6-srv/prod-venv/myn6-app.wsgi

      <Directory /opt/myn6-srv/prod-venv>
        WSGIProcessGroup myn6_srv
        Order allow,deny
        Allow from all
      </Directory>

      # Logging of errors and other events:
      ErrorLog \${APACHE_LOG_DIR}/error.log
      # Possible values for the LogLevel directive include:
      # debug, info, notice, warn, error, crit, alert, emerg.
      LogLevel warn

      # Logging of client requests:
      CustomLog \${APACHE_LOG_DIR}/access.log combined

      # It is recommended to uncomment and adjust the following line.
      #ServerAdmin webmaster@yourserver.example.com
    </VirtualHost>
    EOF
    $ sudo mv prod-venv/myn6.apache /etc/apache2/sites-available/myn6
    $ sudo chown root:root /etc/apache2/sites-available/myn6
    $ sudo chmod 644 /etc/apache2/sites-available/myn6
    $ cd /etc/apache2/sites-enabled
    $ sudo ln -s ../sites-available/myn6 001-myn6

You may want or need to adjust the contents of the newly created file
(``/etc/apache2/sites-available/myn6``) -- especially regarding the
following directives (see the comments accompanying them in the file):

* ``WSGIPassAuthorization``,
* ``ErrorLog`` and ``LogLevel``,
* ``CustomLog``,
* ``ServerAdmin``.

.. seealso::

    * About general configuration of Apache:
      http://httpd.apache.org/docs/2.2/configuring.html

    * About ``modwsgi``-specific configuration:
      http://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines

If we have the default Apache configuration on Debian, we need to
disable the default site by removing the symbolic link:

.. code-block:: bash

    $ rm 000-default

Finally, let us restart the Apache daemon.  On Debian GNU/Linux it can
be done by executing:

.. code-block:: bash

    $ sudo service apache2 restart

Our application should be being served now.  Try visiting the
following URL (with any web browser or, for example, with the ``wget``
command-line tool):

``http://<your apache server address>/myn6/incidents.json``

(Of course, ``<your apache server address>`` needs to be replaced with
the actual host address of your Apache server, for example
``127.0.0.1`` or ``localhost``.)
