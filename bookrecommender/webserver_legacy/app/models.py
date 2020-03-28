from app import db,admin
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy import func, desc, select
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import numpy as np
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.view import func
from flask_login import current_user
from flask import redirect,url_for,request
import datetime




class User(db.Model):
	__tablename__ = "users"

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	email = db.Column(db.String(60), index=True, unique=True)
	password = db.Column(db.String(128))
	age = db.Column(db.Integer)
	location = db.Column(db.String(250))
	authenticated = db.Column(db.Boolean, default=False)

	ratings = db.relationship("Rating")
	books_taken = db.relationship('Transaction', backref="Email")

	def set_password(self, password):
		self.password = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password, password)

	@property
	def is_authenticated(self):
		"""Return True if the user is authenticated."""
		return self.authenticated

	@property
	def is_active(self):
		"""Always True, as all users are active."""
		return True

	@property
	def is_anonymous(self):
		"""Always False, as anonymous users aren't supported."""
		return False

	def get_id(self):
		"""Return the email address to satisfy Flask-Login's requirements."""
		return str(self.id)

	def __repr__(self):
		return f"User {self.id} Email {self.email}"

	def __str__(self):
		return self.__repr__()

	## changes to Users Model

	def is_accessible(self):
		return (current_user.name == 'admin' and current_user.is_authenticated)

	def inaccessible_callback(self, name, **kwargs):
		# redirect to login page if user doesn't have access
		return redirect(url_for('login', next=request.url))





class Book(db.Model):
	__tablename__ = "books"

	isbn = db.Column(db.String(13), primary_key=True)
	title = db.Column(db.String(255))
	author = db.Column(db.String(255))
	year_of_pub = db.Column(INTEGER(unsigned=True))
	publisher = db.Column(db.String(255))
	img_url_s = db.Column(db.String(255))
	img_url_m = db.Column(db.String(255))
	img_url_l = db.Column(db.String(255))
	books_isbn = db.relationship('Transaction', backref="ISBN")

	def __repr__(self):
		return "Book {}".format(self.isbn)

	def __str__(self):
		return self.__repr__()



## New Table Transaction
class Transaction(db.Model):

    __tablename__ = "transaction"

    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(120),db.ForeignKey('users.email'),index=True,nullable=False)
    isbn = db.Column(db.String(20),db.ForeignKey('books.isbn'),nullable=False)
    book_name = db.Column(db.String(200),index=True,nullable=False)
    issue_date = db.Column(db.DateTime,default=datetime.datetime.now)
    due_date = db.Column(db.DateTime,default=lambda :(datetime.datetime.now() + datetime.timedelta(days=7)))
    returned = db.Column(db.Boolean,default=False)

    def is_accessible(self):
        return (current_user.name == 'admin' and current_user.is_authenticated)

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))






class Rating(db.Model):
	__tablename__ = "ratings"

	uid = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
	isbn = db.Column(db.String(13), db.ForeignKey("books.isbn"), primary_key=True)
	rating = db.Column(db.Integer)

	def __repr__(self):
		return "Rating {}".format(self.isbn + ", " + str(self.uid))

	def __str__(self):
		return self.__repr__()

class Recommender(object):

	# def __init__(self):
	# 	with open("recsys/explicit_rec.pkl", "rb") as fid:
	# 		self.model = pickle.load(fid)

	def most_rated(self, n=3):
		queried_books = db.session.query(Rating.isbn, func.count(Rating.rating).label('qty')).group_by(Rating.isbn).order_by(desc('qty')).limit(n).all()
		books = []
		for book in queried_books:
			books.append(Book.query.get(book[0]))

		return books

	def top_average_rated(self, n=3):
		queried_books = db.session.query(Rating.isbn,
				func.count(Rating.rating).label('qty'),
				func.avg(Rating.rating).label('avg_rating')
				).group_by(Rating.isbn).order_by(desc('avg_rating'), desc('qty')).limit(n).all()

		books = []
		for book in queried_books:
			books.append(Book.query.get(book[0]))

		return books

	def top_rated(self, n=3):
		queried_books = db.session.query(Rating.isbn, Rating.rating.label('rating')).order_by(desc('rating')).limit(n).all()

		books = []
		for book in queried_books:
			books.append(Book.query.get(book[0]))

		return books

	def top_rated_isbns(self, n=3):
		queried_books = db.session.query(Rating.isbn, Rating.rating.label('rating')).order_by(desc('rating')).limit(n).all()

		books = []
		for book in queried_books:
			books.append(book[0])

		return books

	def recommend(self, n=3):
		queried_books = [b.isbn for b in db.session.query(Book.isbn)]
		queried_books = np.random.choice(queried_books, n, replace=False)

		books = []
		for isbn in queried_books:
			books.append(Book.query.get(isbn))

		return books


## VIEWS NECESSSARY START HERE-------------------------------------------------------------------------

class TransactionView(ModelView):
    can_create = True
    can_edit = False
    column_searchable_list = ['email']
    can_delete = False
    column_list = ['email', 'isbn', 'issue_date', 'due_date','book_name','returned']
    form_columns = ['email', 'isbn', 'issue_date', 'due_date','book_name']

    def is_accessible(self):
        if current_user.is_authenticated :
            return current_user.email == 'admin@vjti.com'
        else: return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class PendingView(ModelView):
    can_edit = False
    can_create = False
    column_editable_list = ['returned']
    can_delete = False
    column_searchable_list = ['email']
    column_list = ['email', 'isbn', 'issue_date', 'due_date', 'book_name', 'returned']


    def get_query(self):
        return self.session.query(self.model).filter(self.model.returned == False)

    def get_count_query(self):
        return self.session.query(func.count('*')).filter(self.model.returned == False)

    def is_accessible(self):
        if current_user.is_authenticated :
            return current_user.email == 'admin@vjti.com'
        else: return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class UserView(ModelView):
    column_exclude_list = ['password','authenticated','age','location']
    form_columns = ['email','password']
    can_create = True
    can_edit = False
    can_delete = False
    column_searchable_list = ['email']

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.password = generate_password_hash(model.password)


    def is_accessible(self):
        if current_user.is_authenticated :
            return current_user.email == 'admin@vjti.com'
        else: return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class BookView(ModelView):
    can_edit = False
    form_columns = ['title','isbn','author','year_of_pub','publisher']
    column_searchable_list = ['isbn']
    column_exclude_list = ['img_url_s', 'img_url_m', 'img_url_l']

    def is_accessible(self):
        if current_user.is_authenticated :
            return current_user.email == 'admin@vjti.com'
        else: return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


admin.add_view(UserView(User,db.session))
admin.add_view(TransactionView(Transaction,db.session,endpoint='first'))
admin.add_view(BookView(Book,db.session))
admin.add_view(PendingView(Transaction,db.session,'Pending',endpoint='second'))
