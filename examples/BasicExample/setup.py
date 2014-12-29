from setuptools import setup, find_packages

requires = [
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'waitress',
    'n6sdk',
]

setup(
    name='basic_example',
    version='0.0.1',
    description='basic_example',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    #author='',
    #author_email='',
    #url='',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    #tests_require=requires,
    #test_suite="basic_example.tests",
    entry_points="""\
      [paste.app_factory]
      main = basic_example:main
      """,
)
