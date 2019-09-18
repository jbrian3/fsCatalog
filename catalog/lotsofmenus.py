from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Category, Base, MenuItem, User

engine = create_engine('sqlite:///categorymenu.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

user1 = User(username="Rui", email="rui.jiang@gmail.com")
session.add(user1)
session.commit()


category1 = Category(title="Snowboarding")
session.add(category1)
session.commit()


category2 = Category(title="Skating")

session.add(category2)
session.commit()


menuItem1 = MenuItem(title="Goggles",
                     description="Juicy grilled veggie patty with tomato\
 mayo and lettuce",
                     category=category1,
                     user_id=user1.id)

session.add(menuItem1)
session.commit()


menuItem2 = MenuItem(title="Snowboard",
                     description="with garlic and parmesan",
                     category=category1,
                     user_id=user1.id)

session.add(menuItem2)
session.commit()


print "added items!"
