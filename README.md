---
title: Code Review Environment
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review Environment

An OpenEnv RL environment where an AI agent reviews pull requests and identifies bugs, security vulnerabilities, and logic errors.

## What it does

The agent receives a pull request diff and must identify all planted issues. A deterministic grader scores performance 0.0–1.0 based on how many real issues were found minus a penalty for false positives.

## Tasks

| Task | Difficulty | Description |
|------|-----------|-------------|
| task1_easy | Easy | 20-line auth module with one off-by-one error |
| task2_medium | Medium | 2-file API change with a race condition and missing auth check |
| task3_hard | Hard | 4-file reporting module with SQL injection, double discount bug, missing db.commit(), and one red herring |

## Baseline scores

| Task | Score |
|------|-------|
| task1_easy | 0.70 |
| task2_medium | 1.00 |
| task3_hard | 0.13 |

## Reward function

- Base score = bugs found / total bugs planted
- False positive penalty = 0.1 per false positive (capped at 0.3)
- Final score = max(0.0, base score - penalty)

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /reset | POST | Start a new episode |
| /step | POST | Submit a review, get reward back |
| /state | GET | Get current episode state |
| /tasks | GET | List all tasks and action schema |
| /grader | POST | Score an action against a task |
| /baseline | GET | Run baseline agent on all 3 tasks |

## Quick start
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
