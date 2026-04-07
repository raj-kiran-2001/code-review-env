import json
from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field, field_validator
from typing import List


class IssueReport(BaseModel):
    """A single issue found by the agent in the PR."""
    file: str = Field(..., description="Filename where the issue was found")
    line: int = Field(..., description="Line number of the issue")
    issue_type: str = Field(..., description="Type: bug / security / style / performance")
    description: str = Field(..., description="Description of the issue")


class CodeReviewAction(Action):
    """Action for the Code Review environment — agent's full review of a PR."""
    issues: List[IssueReport] = Field(default_factory=list, description="List of issues found")
    summary: str = Field(default="", description="Overall review summary")
    @field_validator("issues", mode="before")
    @classmethod
    def _parse_issues_string(cls, v):
        """Accept a JSON string for issues (sent by the web playground)."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            return json.loads(v)
        return v

class CodeReviewObservation(Observation):
    """Observation returned to the agent — the PR to review."""
    task_id: str = Field(default="", description="Which task this is")
    difficulty: str = Field(default="", description="easy / medium / hard")
    pr_title: str = Field(default="", description="Title of the pull request")
    pr_description: str = Field(default="", description="PR description")
    diff: str = Field(default="", description="The full code diff")
    instructions: str = Field(default="", description="What the agent should do")