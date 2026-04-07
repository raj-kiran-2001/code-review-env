---
title: Code Review Environment
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review Environment

An OpenEnv RL environment where an AI agent reviews pull requests and identifies bugs, security vulnerabilities, and logic errors — with **multi-step iterative feedback**.

## What it does

The agent receives a pull request diff and must identify all planted issues. It gets **up to 3 attempts** per episode. After each attempt the environment returns structured feedback (how many bugs were found, how many remain, false-positive count, and — from attempt 2 — file-level hints). A deterministic grader scores performance strictly within (0, 1).

## Why this matters (Real-world utility)

Code review is one of the most common, high-stakes tasks in software engineering. Reviewers must find subtle bugs across multiple files, distinguish real issues from red herrings, and avoid false alarms. This environment models that challenge faithfully:
- **Multi-file diffs** with realistic code patterns
- **Bug variety**: off-by-one, race conditions, SQL injection, logic errors, missing cleanup
- **Red herrings**: code that *looks* suspicious but is actually safe
- **Iterative refinement**: mirrors real review workflows where feedback drives deeper analysis

## Tasks

| Task | Difficulty | Bugs | Description |
|------|-----------|------|-------------|
| task1_easy | Easy | 1 | 20-line auth module with one off-by-one error and undefined variable |
| task2_medium | Medium | 2 | 2-file change with a race condition and missing auth check |
| task3_hard | Hard | 3 + 1 red herring | Reporting module with SQL injection, double discount, missing db.commit(), and a safe-but-suspicious query |

## Action space

```json
{
  "issues": [
    {
      "file": "string — filename from the diff header",
      "line": "int — line number where the issue occurs",
      "issue_type": "string — bug | security | style | performance",
      "description": "string — clear description of the root cause"
    }
  ],
  "summary": "string — overall review summary"
}
```

## Observation space

| Field | Type | Description |
|-------|------|-------------|
| task_id | string | Current task identifier |
| difficulty | string | easy / medium / hard |
| pr_title | string | Title of the pull request |
| pr_description | string | PR description |
| diff | string | Full unified diff |
| instructions | string | Initial instructions or feedback from previous attempt |
| done | bool | Whether the episode has ended |
| reward | float | Current score in (0, 1) |

## Reward function

- **Base score** = bugs correctly found / total planted bugs
- **False positive penalty** = 0.1 per false positive (capped at 0.3)
- **Final score** = clamp(max(0.0, base − penalty), 0.001, 0.999)
- Reward is provided at **every step**, enabling partial-progress signal
- Perfect review (all bugs, zero FPs) triggers early episode termination

## Multi-step interaction

```
reset() → obs (diff + instructions, done=False)
  ↓
step(review_1) → obs (reward + feedback, done=False)
  ↓
step(review_2) → obs (reward + file hints, done=False)
  ↓
step(review_3) → obs (final reward, done=True)
```

The agent can terminate early if it achieves a perfect review.

## Baseline scores

| Task | Score |
|------|-------|
| task1_easy | 0.999 |
| task2_medium | 0.999 |
| task3_hard | 0.999 |

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /reset | POST | Start a new episode |
| /step | POST | Submit a review, get reward + feedback back |
| /state | GET | Get current episode state |
| /tasks | GET | List all tasks and action schema |
| /grader | POST | Score an action against a task |
| /baseline | GET | Run baseline agent on all 3 tasks |

## Setup and usage

### Environment variables

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your-token-here"
```

### Run locally

```bash
pip install -r requirements.txt
python inference.py
```

### Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

### Client usage

```python
from openenv import EnvClient

env = EnvClient("https://rajkiran2001-code-review-env.hf.space")
obs = env.reset()
print(obs)
```

## Built with

- OpenEnv framework
- FastAPI + Pydantic
- Meta x Hugging Face x Scaler OpenEnv Hackathon 2025
