from setuptools import setup, find_packages

setup(
    name='transmogrifier_ploneblueprints',
    version='1.0.0',
    description="",
    long_description=(open('README.rst').read() + '\n' +
                      open('CHANGES.rst').read()),
    # Get more strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Programming Language :: Python',
    ],
    keywords='',
    author='Asko Soukka',
    author_email='asko.soukka@iki.fi',
    url='https://github.com/datakurre/transmogrifier_ploneblueprints/',
    license='GPL',
    packages=find_packages('src', exclude=['ez_setup']),
    package_dir={'': 'src'},
    namespace_packages=[],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'venusianconfiguration',
        'transmogrifier [path]',
        'Plone',
        'plone.api',
        'collective.atrfc822'
    ],
    extras_require={'test': [
        'plone.testing',
        'plone.app.testing',
        'plone.app.contenttypes'
    ]},
    entry_points="""
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = transmogrifier
    """
)
