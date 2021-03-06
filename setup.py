import os.path as osp

from setuptools import setup, find_packages

setup_dir = osp.dirname(osp.abspath(__file__))


with open(osp.join(setup_dir, 'requirements')) as f:
    requirements = []
    dep_links = []
    for line in f:
        if not line.strip():
            continue
        req = line.split('\t')
        requirements.append(req[0])
        try:
            dep_links.append(req[1])
        except IndexError:
            pass


with open(osp.join(setup_dir, 'README.rst')) as f:
    long_description = f.read()


setup(
    name="n6sdk",
    version='0.6.2',
    packages=find_packages(),
    dependency_links=dep_links,
    install_requires=requirements,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'n6sdk_api_test = n6sdk._api_test_tool.api_test_tool:main',
        ],
        'pyramid.scaffold': [
            'n6sdk = n6sdk.scaffolds:BasicN6SDKTemplate',
        ],
    },
    tests_require=(requirements + ['mock==1.0.1']),
    test_suite="n6sdk.tests",

    description='An *n6*-like REST API server framework.',
    long_description=long_description,
    url='https://github.com/CERT-Polska/n6sdk',
    maintainer='CERT Polska',
    maintainer_email='n6@cert.pl',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pyramid',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    keywords='n6 network incident exchange rest api library framework',
)
