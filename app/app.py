import os

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

PRIORITIES = ("low", "medium", "high")
DEFAULT_PRIORITY = "medium"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(
        db.String(10), nullable=False, default=DEFAULT_PRIORITY
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "priority": self.priority,
        }


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///tasks.db"
    )
    app.config["APP_VERSION"] = os.getenv("APP_VERSION", "dev")
    if config:
        app.config.update(config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    def validate_priority(value):
        if value is None:
            return DEFAULT_PRIORITY, None
        if value not in PRIORITIES:
            return None, "priority must be one of: low, medium, high"
        return value, None

    @app.get("/")
    def index():
        return render_template("index.html", version=app.config["APP_VERSION"])

    @app.get("/health")
    def health():
        # Liveness: the process is up (does not check the database)
        return jsonify(status="ok", version=app.config["APP_VERSION"])

    @app.get("/ready")
    def ready():
        # Readiness: the app can reach the database
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ready")
        except Exception:
            return jsonify(status="not ready"), 503

    @app.get("/api/tasks")
    def list_tasks():
        query = Task.query
        priority = request.args.get("priority")
        if priority:
            if priority not in PRIORITIES:
                return jsonify(error="invalid priority filter"), 400
            query = query.filter_by(priority=priority)
        tasks = query.order_by(Task.id).all()
        return jsonify([t.to_dict() for t in tasks])

    @app.post("/api/tasks")
    def create_task():
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify(error="title is required"), 400
        priority, err = validate_priority(data.get("priority"))
        if err:
            return jsonify(error=err), 400
        task = Task(title=title, priority=priority)
        db.session.add(task)
        db.session.commit()
        return jsonify(task.to_dict()), 201

    @app.put("/api/tasks/<int:task_id>")
    def update_task(task_id):
        task = db.get_or_404(Task, task_id)
        data = request.get_json(silent=True) or {}
        if "title" in data:
            title = (data["title"] or "").strip()
            if not title:
                return jsonify(error="title cannot be empty"), 400
            task.title = title
        if "done" in data:
            task.done = bool(data["done"])
        if "priority" in data:
            priority, err = validate_priority(data["priority"])
            if err:
                return jsonify(error=err), 400
            task.priority = priority
        db.session.commit()
        return jsonify(task.to_dict())

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id):
        task = db.get_or_404(Task, task_id)
        db.session.delete(task)
        db.session.commit()
        return "", 204

    return app
