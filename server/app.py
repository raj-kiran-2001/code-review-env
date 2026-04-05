from fastapi import FastAPI
from fastapi.responses import JSONResponse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv is required. Run: uv sync") from e

try:
    from models import CodeReviewAction, CodeReviewObservation
    from server.code_review_env_environment import CodeReviewEnvironment, TASKS, grade
except ModuleNotFoundError:
    try:
        from ..models import CodeReviewAction, CodeReviewObservation
        from .code_review_env_environment import CodeReviewEnvironment, TASKS, grade
    except ImportError:
        from models import CodeReviewAction, CodeReviewObservation
        from server.code_review_env_environment import CodeReviewEnvironment, TASKS, grade


app = create_app(
    CodeReviewEnvironment,
    CodeReviewAction,
    CodeReviewObservation,
    env_name="code_review_env",
    max_concurrent_envs=10,
)



@app.get("/tasks")
def list_tasks():
    """Return all tasks and the action schema."""
    return {
        "tasks": [
            {
                "id": tid,
                "difficulty": t["difficulty"],
                "pr_title": t["pr_title"],
                "description": t["pr_description"][:120] + "...",
            }
            for tid, t in TASKS.items()
        ],
        "action_schema": CodeReviewAction.model_json_schema(),
    }


@app.post("/grader")
def grader_endpoint(task_id: str, action: CodeReviewAction):
    """Score an agent's action against a task's planted bugs."""
    if task_id not in TASKS:
        return JSONResponse(status_code=404, content={"error": f"Unknown task_id: {task_id}"})
    result = grade(action, task_id)
    return result


@app.get("/baseline")
def baseline_endpoint():
    """
    Run a naive baseline agent against all 3 tasks and return scores.
    Used by judges to verify the environment produces valid reward signals.
    """
    from models import IssueReport

    baseline_actions = {
        "task1_easy": CodeReviewAction(
            issues=[IssueReport(
                file="auth.py", line=24, issue_type="bug",
                description="off-by-one error and users variable not defined in scope of get_all_users"
            )],
            summary="Found off-by-one error in loop"
        ),
        "task2_medium": CodeReviewAction(
            issues=[
                IssueReport(
                    file="orders.py", line=11, issue_type="bug",
                    description="race condition — inventory check is outside the lock, not atomic"
                ),
                IssueReport(
                    file="api.py", line=19, issue_type="security",
                    description="admin endpoint has no authentication or access control check"
                ),
            ],
            summary="Found race condition and missing auth on admin route"
        ),
        "task3_hard": CodeReviewAction(
            issues=[
                IssueReport(
                    file="reports.py", line=11, issue_type="security",
                    description="SQL injection via f-string concatenation in search_users"
                ),
                IssueReport(
                    file="reports.py", line=22, issue_type="bug",
                    description="discount applied twice — wrong calculation"
                ),
                IssueReport(
                    file="reports.py", line=55, issue_type="bug",
                    description="missing db.commit() so audit logs are never persisted"
                ),
            ],
            summary="Found SQL injection, double discount, missing commit"
        ),
    }

    results = {}
    for task_id, action in baseline_actions.items():
        result = grade(action, task_id)
        results[task_id] = result

    return {
        "baseline_scores": {tid: r["score"] for tid, r in results.items()},
        "details": results,
    }


def main():
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
