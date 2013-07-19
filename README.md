ckanext-silk
============

A plugin to integrate Silk Link Discovery Framework into CKAN.

Tested with CKAN 1.8

 Installation
--------------

**Install plugin**

    python setup.py install
        
**Update CKAN development.ini file to load the plugin**

    ckan.plugins = stats silk
    
**Initialize new tables on CKAN database (Change user & pass)**

    python ckanext/silk/model/initDB.py
    
**Silk installation**

Download Silk from http://wifo5-03.informatik.uni-mannheim.de/bizer/silk/. Tested with version 2.5.3

Extract file to some system directory

Add plugin configuration variables to CKAN development.ini

    [plugin:silk]
    silk_home = 'some_dir/silk_2.5.3'

    
**Celery task queue initialization**
This plugin uses Celery (http://celeryproject.org/) for task queueing. 

Start the CKAN instance

    paster serve development.ini
    
Start the Celery server

    paster celeryd run
