from flask import flash, redirect, url_for
from functools import wraps
from flask_login import current_user

def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash("Access denied.", "danger")
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        return wrapper
    return decorator
