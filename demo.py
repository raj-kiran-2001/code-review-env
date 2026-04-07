"""Quick demo — runs one episode against the live HF Space."""
import requests

BASE = "https://rajkiran2001-code-review-env.hf.space"

obs = requests.post(f"{BASE}/reset", json={"task_id": "task1_easy"}).json()
print("PR Title:", obs["observation"]["pr_title"])
print("Diff preview:", obs["observation"]["diff"][:200])

result = requests.get(f"{BASE}/baseline").json()
print("Baseline scores:", result["baseline_scores"])