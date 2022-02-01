from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_login.mixins import AnonymousUserMixin
from forms import CreatePostForm, UserForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app, size=200)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
manager = LoginManager()
manager.init_app(app)

#Database Tables
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")
    
class BlogPost(db.Model):
    __tablename__ = 'blogpost'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")
    
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # child of User
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    comment_author = relationship("User", back_populates="comments")
    # child of BlogPost
    post_id = db.Column(db.Integer, db.ForeignKey("blogpost.id"))
    parent_post = relationship("BlogPost", back_populates="comments") 
    text = db.Column(db.Text, nullable=False)
#db.create_all() # if you want to change or accidentally delete the database, just uncomment.

def get_username():
    if type(current_user._get_current_object()) is not AnonymousUserMixin:
        return current_user.username

def needs_admin(function):
    """ Wrapper function. Ensures only admin can access decorated routes."""
    @wraps(function) #to ensure it is compatible with multiple decorators
    def secure(*args, **kwargs):
        if current_user.is_authenticated:
            # First registered account is the Admin. If you want a different admin condition, 
            # eg, a specific name. You will have to do it here.
            if current_user.id == 1: 
                return function(*args,**kwargs)
        return manager.unauthorized()
    return secure

@manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    admin = False
    if current_user.is_authenticated:
        if current_user.id == 1:
            admin=True
    
    return render_template("index.html", 
                            all_posts=posts, 
                            username=get_username(), 
                            logged_in=current_user.is_authenticated,
                            is_admin=admin)


@app.route('/register', methods=['POST','GET'])
def register():
    form = UserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, password=generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('get_all_posts'))
    
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET","POST"])
def login():
    form = UserForm()
    if form.validate_on_submit():
        user = User.query.filter(User.username==form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Incorrect Password')
        else:
            flash("Username is not registered.")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form=CommentForm()
    admin=False
    if current_user.is_authenticated:
        if current_user.id == 1:
            admin=True
    if form.validate_on_submit():
        db.session.add(Comment(text=form.text.data, comment_author=current_user, parent_post=requested_post))
        db.session.commit()
        
    return render_template("post.html", 
                           post=requested_post, 
                           username=get_username(), 
                           logged_in=current_user.is_authenticated,
                           is_admin=admin,
                           form=form)


@app.route("/about")
def about():
    return render_template("about.html", username=get_username(), logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", username=get_username(), logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=["POST","GET"])
@needs_admin
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, username=get_username(), logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>")
@needs_admin
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, username=get_username(), logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@needs_admin
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)
