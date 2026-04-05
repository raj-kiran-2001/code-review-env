from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from models import CodeReviewAction, CodeReviewObservation
except ImportError:
    try:
        from ..models import CodeReviewAction, CodeReviewObservation
    except ImportError:
        from models import CodeReviewAction, CodeReviewObservation


# ── TASK DEFINITIONS ────────────────────────────────────────────────────────

TASKS = {
    "task1_easy": {
        "difficulty": "easy",
        "pr_title": "Add user input sanitization to login form",
        "pr_description": "This PR adds basic input sanitization to the login endpoint to prevent empty username submissions.",
        "diff": """\
--- a/auth.py
+++ b/auth.py
@@ -1,20 +1,28 @@
 def get_user(username):
     users = {
         "alice": {"password": "secret123", "role": "admin"},
         "bob":   {"password": "pass456",   "role": "user"},
     }
     return users.get(username)

 def login(username, password):
+    if username == "":
+        return {"error": "Username cannot be empty"}
+
     user = get_user(username)
+
     if user is None:
         return {"error": "User not found"}
-    if user["password"] == password:
+
+    if user["password"] == password:
         return {"success": True, "role": user["role"]}
-    return {"error": "Wrong password"}
+
+    return {"error": "Invalid credentials"}

 def get_all_users():
     result = []
     for i in range(0, len(users) + 1):   # BUG: off-by-one, users not defined here
         result.append(users[i])
     return result
""",
        "planted_bugs": [
            {
                "id": "bug_1",
                "file": "auth.py",
                "line": 24,
                "keywords": ["off-by-one", "index", "range", "len", "out of range", "users not defined", "NameError", "scope"],
                "description": "off-by-one error and undefined variable 'users' in get_all_users()"
            }
        ]
    },

    "task2_medium": {
        "difficulty": "medium",
        "pr_title": "Add concurrent order processing with shared inventory",
        "pr_description": "Refactors order processing to handle multiple simultaneous orders and adds a new admin endpoint.",
        "diff": """\
--- a/orders.py
+++ b/orders.py
@@ -1,35 +1,50 @@
 import threading

 inventory = {"apple": 10, "banana": 5, "cherry": 2}
 lock = threading.Lock()

 def process_order(item, quantity):
-    if inventory.get(item, 0) >= quantity:
-        inventory[item] -= quantity
-        return {"status": "ok", "item": item, "qty": quantity}
-    return {"status": "out_of_stock"}
+    # BUG: lock acquired but inventory check and update not atomic
+    current = inventory.get(item, 0)
+    if current >= quantity:
+        lock.acquire()
+        inventory[item] -= quantity
+        lock.release()
+        return {"status": "ok", "item": item, "qty": quantity}
+    return {"status": "out_of_stock"}

--- a/api.py
+++ b/api.py
@@ -1,15 +1,25 @@
 from flask import Flask, request, jsonify
 app = Flask(__name__)

 @app.route("/order", methods=["POST"])
 def order():
     data = request.get_json()
     return jsonify(process_order(data["item"], data["quantity"]))

+@app.route("/admin/orders", methods=["GET"])
+def admin_orders():
+    # BUG: no authentication check on admin endpoint
+    return jsonify({"all_orders": get_all_orders()})
+
 @app.route("/health", methods=["GET"])
 def health():
     return jsonify({"status": "ok"})
""",
        "planted_bugs": [
            {
                "id": "bug_1",
                "file": "orders.py",
                "line": 11,
                "keywords": ["race condition", "lock", "atomic", "thread", "concurrent", "not protected", "outside lock"],
                "description": "race condition — inventory check happens outside the lock"
            },
            {
                "id": "bug_2",
                "file": "api.py",
                "line": 19,
                "keywords": ["auth", "authentication", "unauthorized", "admin", "no check", "unprotected", "access control"],
                "description": "admin endpoint has no authentication check"
            }
        ]
    },

    "task3_hard": {
        "difficulty": "hard",
        "pr_title": "Refactor reporting module: add filters, discount logic, and DB search",
        "pr_description": "Major refactor of the reporting module. Adds user filtering, discount calculation, full-text DB search, and audit logging.",
        "diff": """\
--- a/reports.py
+++ b/reports.py
@@ -1,80 +1,130 @@
 import sqlite3
 from datetime import datetime

 def get_db():
     return sqlite3.connect("app.db")

 def search_users(query):
-    db = get_db()
-    cursor = db.execute("SELECT * FROM users WHERE name = ?", (query,))
-    return cursor.fetchall()
+    db = get_db()
+    # BUG: SQL injection — query concatenated directly
+    cursor = db.execute(f"SELECT * FROM users WHERE name = '{query}'")
+    return cursor.fetchall()

 def calculate_discount(user_type, amount):
     if user_type == "premium":
         discount = 0.2
     elif user_type == "student":
         discount = 0.1
     else:
         discount = 0.0
-    return amount * (1 - discount)
+    # BUG: discount applied twice — subtracted then multiplied again
+    discounted = amount - (amount * discount)
+    return discounted * (1 - discount)

 def generate_report(start_date, end_date, user_type=None):
     db = get_db()
     rows = db.execute(
         "SELECT * FROM orders WHERE date BETWEEN ? AND ?",
         (start_date, end_date)
     ).fetchall()

     total = 0
     for row in rows:
         amount = row[3]
         utype  = row[4]
         total += calculate_discount(utype, amount)

     return {"total": total, "rows": len(rows)}

 def get_user_activity(user_id):
     db = get_db()
     # NOTE: this looks suspicious but is actually fine — read-only query
     raw = f"user_{user_id}_activity"
     cursor = db.execute("SELECT * FROM activity WHERE key = ?", (raw,))
     return cursor.fetchall()

 def audit_log(action, user_id):
     timestamp = datetime.now().isoformat()
     db = get_db()
     db.execute(
         "INSERT INTO audit (action, user_id, ts) VALUES (?, ?, ?)",
         (action, user_id, timestamp)
     )
     # BUG: db.commit() missing — audit logs never actually saved
""",
        "planted_bugs": [
            {
                "id": "bug_1",
                "file": "reports.py",
                "line": 11,
                "keywords": ["sql injection", "injection", "f-string", "format", "concatenat", "unsanitized", "parameterized"],
                "description": "SQL injection via f-string in search_users()"
            },
            {
                "id": "bug_2",
                "file": "reports.py",
                "line": 22,
                "keywords": ["discount", "twice", "double", "applied twice", "wrong", "calculation", "incorrect"],
                "description": "discount applied twice in calculate_discount()"
            },
            {
                "id": "bug_3",
                "file": "reports.py",
                "line": 55,
                "keywords": ["commit", "not saved", "missing commit", "transaction", "rollback", "persist", "never saved"],
                "description": "db.commit() missing — audit logs never persisted"
            },
            {
                "id": "red_herring",
                "file": "reports.py",
                "line": 43,
                "keywords": [],
                "description": "RED HERRING — get_user_activity uses parameterized query, is safe",
                "is_red_herring": True
            }
        ]
    }
}


# ── GRADER ──────────────────────────────────────────────────────────────────

def grade(action: CodeReviewAction, task_id: str) -> dict:
    task = TASKS[task_id]
    planted = [b for b in task["planted_bugs"] if not b.get("is_red_herring", False)]
    red_herrings = [b for b in task["planted_bugs"] if b.get("is_red_herring", False)]

    found_ids = []
    missed_ids = []
    false_positives = 0

    for bug in planted:
        matched = False
        for agent_issue in action.issues:
            line_close = abs(agent_issue.line - bug["line"]) <= 3
            keyword_hit = any(
                kw.lower() in agent_issue.description.lower()
                for kw in bug["keywords"]
            )
            if line_close and keyword_hit:
                matched = True
                break
        if matched:
            found_ids.append(bug["id"])
        else:
            missed_ids.append(bug["id"])

    # penalise flagging red herrings
    for rh in red_herrings:
        for agent_issue in action.issues:
            line_close = abs(agent_issue.line - rh["line"]) <= 3
            if line_close:
                false_positives += 1

    # penalise general false positives (issues not near any planted bug)
    all_bug_lines = [b["line"] for b in task["planted_bugs"]]
    for agent_issue in action.issues:
        near_any = any(abs(agent_issue.line - bl) <= 3 for bl in all_bug_lines)
        if not near_any:
            false_positives += 1

    raw = len(found_ids) / len(planted) if planted else 0.0
    penalty = min(false_positives * 0.1, 0.3)
    score = round(max(0.0, raw - penalty), 2)

    return {
        "score": score,
        "found": found_ids,
        "missed": missed_ids,
        "false_positives": false_positives,
        "total_planted": len(planted)
    }


# ── ENVIRONMENT ─────────────────────────────────────────────────────────────

class CodeReviewEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id = "task1_easy"

    def reset(self, task_id: str = "task1_easy", **kwargs) -> CodeReviewObservation:
        if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
            task_id = kwargs["metadata"].get("task_id", task_id)
        if task_id not in TASKS:
            task_id = "task1_easy"
        self._current_task_id = task_id
        self._state = State(episode_id=str(uuid4()), step_count=0)

        task = TASKS[task_id]
        return CodeReviewObservation(
            task_id=task_id,
            difficulty=task["difficulty"],
            pr_title=task["pr_title"],
            pr_description=task["pr_description"],
            diff=task["diff"],
            instructions=(
                "Review this pull request carefully. "
                "Identify all bugs, security issues, and logic errors. "
                "For each issue report the filename, line number, issue type, and a clear description."
            ),
            done=False,
            reward=0.0,
        )

    def step(self, action: CodeReviewAction) -> CodeReviewObservation:
        self._state.step_count += 1
        result = grade(action, self._current_task_id)

        task = TASKS[self._current_task_id]
        return CodeReviewObservation(
            task_id=self._current_task_id,
            difficulty=task["difficulty"],
            pr_title=task["pr_title"],
            pr_description=task["pr_description"],
            diff=task["diff"],
            instructions="Review complete.",
            done=True,
            reward=result["score"],
            metadata=result,
        )

    @property
    def state(self) -> State:
        return self._state