import os
import json
import sys
from openai import OpenAI

API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK    = "code_review_env"

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# ── IMPORT ENV ───────────────────────────────────────────────────────────────
from models import CodeReviewAction, CodeReviewObservation, IssueReport
from server.code_review_env_environment import CodeReviewEnvironment, grade

TASKS = ["task1_easy", "task2_medium", "task3_hard"]


def build_prompt(obs: CodeReviewObservation) -> str:
    return f"""You are an expert code reviewer. Review the following pull request and identify ALL bugs, security vulnerabilities, and logic errors.

PR Title: {obs.pr_title}
PR Description: {obs.pr_description}

Diff:
{obs.diff}

Instructions: {obs.instructions}

Respond ONLY with a valid JSON object in exactly this format, no markdown, no explanation:
{{
  "issues": [
    {{
      "file": "<filename>",
      "line": <line_number_integer>,
      "issue_type": "<bug|security|style|performance>",
      "description": "<clear description of the issue>"
    }}
  ],
  "summary": "<overall review summary>"
}}"""


def run_episode(task_id: str) -> dict:
    env  = CodeReviewEnvironment()
    obs  = env.reset(task_id)

    # ── [START] ──────────────────────────────────────────────────────────────
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    step_num    = 0
    all_rewards = []
    success     = False
    score       = 0.0

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": build_prompt(obs)}],
            temperature=0.1,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()

        # strip markdown fences if model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data   = json.loads(raw)
        issues = [
            IssueReport(
                file=i.get("file", ""),
                line=int(i.get("line", 0)),
                issue_type=i.get("issue_type", "bug"),
                description=i.get("description", ""),
            )
            for i in data.get("issues", [])
        ]
        action = CodeReviewAction(issues=issues, summary=data.get("summary", ""))
        error  = "null"

    except json.JSONDecodeError as e:
        action = CodeReviewAction(issues=[], summary="parse error")
        error  = f"json_parse_error: {str(e)[:80]}"

    except Exception as e:
        action = CodeReviewAction(issues=[], summary="api error")
        error  = f"api_error: {str(e)[:80]}"

    # step the environment
    obs_final = env.step(action)
    result    = grade(action, task_id)
    step_num  = 1
    reward    = result["score"]
    done      = True
    all_rewards.append(reward)
    score     = reward
    success   = score > 0.0

    # ── [STEP] ───────────────────────────────────────────────────────────────
    action_str = f"issues={len(action.issues)}"
    print(
        f"[STEP] step={step_num} action={action_str} "
        f"reward={reward:.2f} done={str(done).lower()} error={error}",
        flush=True
    )

    # ── [END] ────────────────────────────────────────────────────────────────
    rewards_str = ",".join(f"{r:.2f}" for r in all_rewards)
    print(
        f"[END] success={str(success).lower()} steps={step_num} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True
    )

    return {"task_id": task_id, "score": score, "found": result["found"], "missed": result["missed"]}


def main():
    all_results = {}
    for task_id in TASKS:
        result = run_episode(task_id)
        all_results[task_id] = result["score"]

    # summary to stderr so it doesn't interfere with stdout log format
    print("\n--- SUMMARY ---", file=sys.stderr)
    for task_id, score in all_results.items():
        print(f"  {task_id}: {score:.2f}", file=sys.stderr)
    avg = sum(all_results.values()) / len(all_results)
    print(f"  Average: {avg:.2f}", file=sys.stderr)


if __name__ == "__main__":
    main()