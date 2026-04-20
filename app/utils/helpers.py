from flask import session
from app.extensions import db
from app.models.user import User
from functools import wraps
from flask import redirect, url_for

def get_current_user():
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function