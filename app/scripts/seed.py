"""Populate the database with 10 sample tasks.

Usage (from the app/ folder):
    python scripts/seed.py
    DATABASE_URL=postgresql://user:pass@localhost:5432/tasks python scripts/seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import Task, create_app, db  # noqa: E402

SAMPLE_TASKS = [
    ("Configure OSPF on lab routers", "high"),
    ("Review VLAN design", "medium"),
    ("Write Ansible inventory", "high"),
    ("Update README documentation", "low"),
    ("Test Calico network policy", "medium"),
    ("Rotate SSH keys", "high"),
    ("Clean old Docker images", "low"),
    ("Check chrony time sync", "medium"),
    ("Prepare GHCR push workflow", "high"),
    ("Take project screenshots", "low"),
]


def main():
    app = create_app()
    with app.app_context():
        for title, priority in SAMPLE_TASKS:
            db.session.add(Task(title=title, priority=priority))
        db.session.commit()
        print(f"Seeded {len(SAMPLE_TASKS)} tasks.")


if __name__ == "__main__":
    main()
