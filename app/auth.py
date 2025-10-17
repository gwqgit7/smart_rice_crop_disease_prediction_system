from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db


bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = True
            flash('Username is required.', 'danger')
        elif not password:
            error = True
            flash('Password is required.', 'danger')
        
        if error is None:
            try:
                db.execute(
                    'INSERT INTO user (username, password) VALUES (?, ?)',
                    (username, generate_password_hash(password),)
                )
                db.commit()
            except db.IntegrityError:
                error = True
                flash("Username existed.", 'danger')
                db.rollback()
            else:
                flash('Registered successfully! You can now log in.', 'success')
                return redirect(url_for("auth.login"))

    return render_template('register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = True
            flash('Wrong username.', 'danger')
        elif not check_password_hash(user['password'], password):
            error = True
            flash('Wrong password.', 'danger')
        
        if error is None:
            session.clear()
            session['user_id'] = user['user_id']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home.index'))

    return render_template('login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE user_id = ?', (user_id,)
        ).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view


@bp.route('/profile')
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE user_id = ?', (session['user_id'],)).fetchone()
    return render_template('profile.html', user=user)


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE user_id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        current_pw = request.form['current_password']
        new_pw = request.form['new_password']

        if not check_password_hash(user['password'], current_pw):
            flash('Incorrect current password.', 'danger')
        else:
            db.execute('UPDATE user SET password = ? WHERE user_id = ?',
                       (generate_password_hash(new_pw), session['user_id']))
            db.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))

    return render_template('change_password.html', user=user)


@bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))
