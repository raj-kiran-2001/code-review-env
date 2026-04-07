# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Code Review Env Environment Client."""

from typing import Dict, List

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import CodeReviewAction, CodeReviewObservation


class CodeReviewEnv(
    EnvClient[CodeReviewAction, CodeReviewObservation, State]
):
    """
    Client for the Code Review Env Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with CodeReviewEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.pr_title)
        ...
        ...     from models import IssueReport
        ...     action = CodeReviewAction(
        ...         issues=[IssueReport(file="auth.py", line=24,
        ...                             issue_type="bug",
        ...                             description="off-by-one error")],
        ...         summary="Found off-by-one"
        ...     )
        ...     result = client.step(action)
        ...     print(result.reward)

    Example with Docker:
        >>> client = CodeReviewEnv.from_docker_image("code_review_env-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     result = client.step(CodeReviewAction(issues=[], summary="No issues"))
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: CodeReviewAction) -> Dict:
        """Convert CodeReviewAction to JSON payload for step message.

        Args:
            action: CodeReviewAction instance with issues and summary.

        Returns:
            Dictionary representation suitable for JSON encoding.
        """
        return {
            "issues": [
                {
                    "file": issue.file,
                    "line": issue.line,
                    "issue_type": issue.issue_type,
                    "description": issue.description,
                }
                for issue in action.issues
            ],
            "summary": action.summary,
        }

    def _parse_result(self, payload: Dict) -> StepResult[CodeReviewObservation]:
        """Parse server response into StepResult[CodeReviewObservation].

        Args:
            payload: JSON response data from server.

        Returns:
            StepResult with CodeReviewObservation.
        """
        obs_data = payload.get("observation", {})
        observation = CodeReviewObservation(
            task_id=obs_data.get("task_id", ""),
            difficulty=obs_data.get("difficulty", ""),
            pr_title=obs_data.get("pr_title", ""),
            pr_description=obs_data.get("pr_description", ""),
            diff=obs_data.get("diff", ""),
            instructions=obs_data.get("instructions", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """Parse server response into State object.

        Args:
            payload: JSON response from state request.

        Returns:
            State object with episode_id and step_count.
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )