import httpx

from common.settings import get_settings

LINEAR_API_URL = "https://api.linear.app/graphql"

ISSUE_CREATE_MUTATION = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) { success issue { identifier } }
}
"""


class LinearNotConfiguredError(Exception):
    pass


class LinearError(Exception):
    pass


async def create_linear_issue(title: str, description: str) -> str:
    """Create an issue in Linear and return its identifier, e.g. MIN-123."""
    settings = get_settings()
    if not settings.LINEAR_API_KEY or not settings.LINEAR_TEAM_ID:
        raise LinearNotConfiguredError

    issue_input = {"teamId": settings.LINEAR_TEAM_ID, "title": title, "description": description}
    if settings.LINEAR_PROJECT_ID:
        issue_input["projectId"] = settings.LINEAR_PROJECT_ID

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            LINEAR_API_URL,
            headers={"Authorization": settings.LINEAR_API_KEY},
            json={"query": ISSUE_CREATE_MUTATION, "variables": {"input": issue_input}},
        )
    response.raise_for_status()
    body = response.json()

    # Linear returns HTTP 200 for GraphQL errors, so check the body too
    result = (body.get("data") or {}).get("issueCreate") or {}
    if body.get("errors") or not result.get("success"):
        msg = f"Linear issueCreate failed: {body.get('errors')}"
        raise LinearError(msg)
    return result["issue"]["identifier"]
