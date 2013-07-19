ckanext-silk
============

A plugin to integrate Silk Link Discovery Framework (http://wifo5-03.informatik.uni-mannheim.de/bizer/silk/) into CKAN.

Tested with CKAN 1.8

 Installation
--------------

**Install plugin**

    python setup.py install
        
**Update CKAN development.ini file to load the plugin**

    ckan.plugins = stats silk
    
**Initialize new tables on CKAN database (Change user & pass)**

    python ckanext/silk/model/initDB.py
    
**Celery task queue initialization**
This plugin uses Celery (http://celeryproject.org/) for task queueing. 

Start the CKAN instance

    paster serve development.ini
    
Start the Celery server

    paster celeryd run
