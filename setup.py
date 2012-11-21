from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
	name='ckanext-silk',
	version=version,
	description="Extension to integrate SILK into CKAN.",
	long_description="""\
	""",
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='Mikel Emaldi',
	author_email='m.emaldi@deusto.es',
	url='http://www.morelab.deusto.es',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.silk'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	
         """
       [ckan.plugins]
       # Add plugins here, eg
       # myplugin=ckanext.silk:PluginClass
       silk=ckanext.silk.plugin:SilkExtension
       """,
)
