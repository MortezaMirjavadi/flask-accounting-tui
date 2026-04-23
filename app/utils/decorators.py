from functools import wraps
from flask import jsonify
from app.utils.helpers import get_user_id_from_request


def require_user(f):
    """Decorator to ensure valid user is present."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id, err = get_user_id_from_request()
        if err:
            return err
        kwargs['user_id'] = user_id
        return f(*args, **kwargs)
    return decorated_function
