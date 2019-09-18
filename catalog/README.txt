Catalog App Introduction:
It includes some fixed categories, under which every logged-in user can login and create new items, but they can only edit or delete items belonging to them.


Installation Instructions:
1.You need to change client_secrets.json file with your own google api settings.


2.Install required Libraries and dependencies
$ pip install -r requirements.txt


Operating Instructions:
1.We use sqlite3 database, you can use lotsofmenus.py to populate the database. If you want to change another database, remember also change the file views.py

2.How to run your application
$ python views.py


Hint: API address setting is /catalog/JSON
