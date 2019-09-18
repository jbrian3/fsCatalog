from flask import (Flask,
                   render_template,
                   url_for,
                   redirect,
                   request,
                   jsonify,
                   flash)
from flask import session as login_session

# Sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from models import Category, Base, MenuItem, User

import random
import string

# for google oAuth2 login
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

from flask_httpauth import HTTPBasicAuth


Base = declarative_base()
auth = HTTPBasicAuth()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Category App"

# Create session and connect to DB
engine = create_engine('sqlite:///categorymenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)


# Making an API endpoint for categories (GET Request)
@app.route('/catalog/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    serializedCategories = []
    for i in categories:
        new_cat = i.serializer
        items = session.query(MenuItem).filter_by(category_id=i.id).all()
        serializedItems = []
        for j in items:
            serializedItems.append(j.serializer)
        new_cat['item'] = serializedItems
        serializedCategories.append(new_cat)
    return jsonify(Category=serializedCategories)


# Home page for categories and latest items
@app.route('/')
@app.route('/restaurant')
@app.route('/catalog/')
def showCategories():
    categories = session.query(Category).all()
    latestItems = session.query(MenuItem).order_by(MenuItem.id).all()[:10]
    if "email" not in login_session:
        return render_template('publiccategories.html',
                               categories=categories,
                               latestItems=latestItems,
                               getCategoryname=getCategoryname,
                               is_authenticated=is_authenticated)
    else:
        return render_template('categories.html',
                               categories=categories,
                               latestItems=latestItems,
                               getCategoryname=getCategoryname,
                               is_authenticated=is_authenticated)


# Items page of a categories
@app.route('/catalog/<categoryname>/items')
def showItems(categoryname):
    categories = session.query(Category).all()
    selected_category = session.query(Category).filter_by(
        title=categoryname).one()
    items = session.query(MenuItem).filter_by(
        category_id=selected_category.id).all()
    count = len(items)
    return render_template('items.html',
                           categories=categories,
                           items=items,
                           category=selected_category,
                           count=count,
                           getCategoryname=getCategoryname,
                           is_authenticated=is_authenticated)


# An item page with details
@app.route('/catalog/<categoryname>/<itemname>')
def itemDetail(categoryname, itemname):
    selected_category = session.query(Category).filter_by(
        title=categoryname).one()
    item = session.query(MenuItem).filter_by(title=itemname).first()
    creator = getUser(item.user_id)
    if 'email' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicitemdetail.html',
                               category=selected_category,
                               item=item,
                               creator=creator,
                               is_authenticated=is_authenticated)
    else:
        return render_template('itemdetail.html',
                               category=selected_category,
                               item=item,
                               is_authenticated=is_authenticated)


# Page to create a new item
@app.route('/catalog/new', methods=['GET', 'POST'])
def newMenuItem():
    if 'email' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        selected_category = session.query(Category).filter_by(
            title=request.form['categoryname']).one()
        newMenuItem = MenuItem(title=request.form['title'],
                               description=request.form['description'],
                               category_id=selected_category.id,
                               user_id=login_session['user_id'])
        session.add(newMenuItem)
        flash('Item %s successfully added' % newMenuItem.title)
        session.commit()
        return redirect(url_for('showItems',
                        categoryname=selected_category.title))
    else:
        categories = session.query(Category).all()
        return render_template('newmenuitem.html',
                               categories=categories,
                               is_authenticated=is_authenticated)


# Page to edit an item
@app.route('/catalog/<itemname>/edit', methods=['GET', 'POST'])
def editMenuItem(itemname):
    editedItem = session.query(MenuItem).filter_by(title=itemname).first()
    if 'email' not in login_session:
        return redirect('/login')
    if editedItem.user_id != login_session['user_id']:
        return "<script>function myFunction(){alert ('You are not \
authorized, please just mind your own items.');}\
</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['title']:
            editedItem.title = request.form['title']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['categoryname']:
            selected_category = session.query(Category).filter_by(
                title=request.form['categoryname']).one()
            editedItem.category_id = selected_category.id
        session.add(editedItem)
        flash('Item %s successfully edited' % editedItem.title)
        session.commit()
        return redirect(url_for('itemDetail',
                                categoryname=getCategoryname(editedItem),
                                itemname=editedItem.title)
                        )
    else:
        categories = session.query(Category).all()
        category = session.query(Category).filter_by(
            id=editedItem.category_id).one()
        return render_template('editMenuItem.html',
                               itemname=itemname,
                               item=editedItem,
                               categories=categories,
                               category=category,
                               is_authenticated=is_authenticated)


# Page to delete an existed item
@app.route('/catalog/<itemname>/delete', methods=['GET', 'POST'])
def deleteMenuItem(itemname):
    toBeDeletedItem = session.query(MenuItem).filter_by(title=itemname).first()
    category = session.query(Category).filter_by(
        id=toBeDeletedItem.category_id).one()
    if 'email' not in login_session:
        return redirect('/login')
    if toBeDeletedItem.user_id != login_session['user_id']:
        return "<script>function myFunction(){alert('You are not \
authorized, please just mind your own items.');}</script>\
<body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(toBeDeletedItem)
        flash('Item %s successfully deleted' % toBeDeletedItem.title)
        session.commit()
        return redirect(url_for('showItems', categoryname=category.title))
    else:
        return render_template('deletemenuitem.html',
                               itemname=itemname,
                               item=toBeDeletedItem,
                               category=category,
                               is_authenticated=is_authenticated)


# Google login page, only entrance
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# Google login process
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    print "code:" + code

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        print "oauth_flow:" + str(oauth_flow)
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        print "credentials:" + str(credentials)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    print "access_token:" + access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    print result
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check to see if user is already logged in
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # If google user doesn't exist locally, create a new user
    if is_registered(login_session['email']) is False:
        createUser(login_session)
        print "login_session1:" + str(login_session)
    login_session['user_id'] = getUserID(login_session['email'])
    print "login_session2:" + str(login_session)
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; \
              height: 300px; \
              border-radius: 150px;\
              -webkit-border-radius: 150px;\
              -moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# Disconnect: Revoke a current user's token and reset login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    # print login_session
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = ('https://accounts.google.com/o/oauth2/revoke?token=%s'
           % login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


"""
Helper functions
"""


# Get user's ID
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).first()
        return user.id
    except AttributeError:
        return 'user is None'


# Get an User by id
def getUser(id):
    user = session.query(User).filter_by(id=id).one()
    return user


# Create a new User
def createUser(login_session):
    newUser = User(username=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    flash('User %s successfully created' % newUser.username)
    session.commit()


# User item to get category
def getCategory(item):
    category = session.query(Category).filter_by(id=item.category_id).one()
    return category


# User item to get category id
def getCategoryname(item):
    category = session.query(Category).filter_by(id=item.category_id).one()
    return category.title


# Check if a user is registered, return true when registered
def is_registered(email):
    users = session.query(User).all()
    for i in range(len(users)):
        if users[i].email == email:
            return True
    return False


# Check if a user is authenticated, return true when authenticated
def is_authenticated():
    user_id = login_session.get('user_id')
    if user_id is not None:
        return True
    else:
        return False


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
