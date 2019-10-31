import flask
import flask_login
from werkzeug.security import generate_password_hash, check_password_hash
from predict import app, db
import predict.models


def process_password(password, password_hash):
    """Processes the password by using werkzeug generated hash
    and check hash functionality.

    Args:
        password (str): The password the user entered to login
        password_hash (str): The generated password hash stored
        for the user
    Returns:
        True if the password_hash matches the input password
        False if password_hash doesn't match input password
    """

    return check_password_hash(password_hash, password)


def create_user(username, password):
    """Attempts to create a new user

    Args:
        username (str): The username for the new user
        password (str): The password for the new user
    Returns:
        True if the user was successfully created, False otherwise.
    """
    user = predict.models.User.query.filter_by(username=username).scalar()

    if user is None:
        password_hash = generate_password_hash(password)
        new_user = predict.models.User(username=username, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()

        return True
    else:
        return False


def authenticate_user(username, password):
    """Checks if the given credentials are correct

    Args:
        username (str): username to check
        password (str): password to check
    Returns:
        True if the given credentials refer to a valid user, False otherwise
    """
    user = load_user(username)

    if user is not None:
        auth = process_password(password, user.password_hash)

        if auth:
            flask_login.login_user(user)
            return True

    return False


def load_user(username):
    """Loads the user object with the given username

    Args:
        username: The username of the user to load
    Returns:
        The user with the given username or None if the user doesn't exist.
    """
    user = predict.models.User.query.filter_by(username=username).first()

    return user
