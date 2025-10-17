from flask import Flask
import os
import db, auth, home, hist


def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'dev-secret-key'
    app.config['DATABASE'] = os.path.join(app.instance_path, 'database.db')

    app.teardown_appcontext(db.close_db)

    app.register_blueprint(auth.bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(hist.bp)

    return app
