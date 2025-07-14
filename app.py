from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import json


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'submissions.db')

def create_app():
    app = Flask(
        __name__,
        static_folder='static',      # optional: add static files later.
        template_folder='templates'
    )
    # Configure SQLite database.
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db = SQLAlchemy(app)

    # Number of items each user must submit.
    N_ITEMS = 5

    class Submission(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user = db.Column(db.String(1), unique=True, nullable=False)  # 'A' or 'B'
        items = db.Column(db.Text, nullable=False)                   # JSON-encoded list.

    @app.before_first_request
    def init_db():
        if not os.path.exists(DB_PATH):
            db.create_all()

    @app.route('/', methods=['GET', 'POST'])
    def choose_user():
        if request.method == 'POST':
            user = request.form.get('user')
            return redirect(url_for('submit_items', user=user))
        return render_template('choose_user.html')

    @app.route('/submit/<user>', methods=['GET', 'POST'])
    def submit_items(user):
        if user not in ('A', 'B'):
            return redirect(url_for('choose_user'))

        if request.method == 'POST':
            items = [request.form.get(f'item{i+1}', '').strip() for i in range(N_ITEMS)]
            if not all(items):
                return render_template('submit.html', user=user, n=N_ITEMS, error='Please fill in all fields.')

            # User submission.
            existing = Submission.query.filter_by(user=user).first()
            payload = json.dumps(items)
            if existing:
                existing.items = payload
            else:
                new_sub = Submission(user=user, items=payload)
                db.session.add(new_sub)
            db.session.commit()

            # Redirect based on whether both users have submitted.
            other_user = 'B' if user == 'A' else 'A'
            if Submission.query.filter_by(user=other_user).first():
                return redirect(url_for('results'))
            return redirect(url_for('waiting', user=user))

        return render_template('submit.html', user=user, n=N_ITEMS)

    @app.route('/waiting/<user>')
    def waiting(user):
        # Polling page until the other user submits.
        return render_template('waiting.html', user=user)

    @app.route('/results')
    def results():
        subA = Submission.query.filter_by(user='A').first()
        subB = Submission.query.filter_by(user='B').first()
        if not (subA and subB):
            return redirect(url_for('choose_user'))

        itemsA = json.loads(subA.items)
        itemsB = json.loads(subB.items)
        return render_template('results.html', itemsA=itemsA, itemsB=itemsB)

    return app


application = create_app()

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
