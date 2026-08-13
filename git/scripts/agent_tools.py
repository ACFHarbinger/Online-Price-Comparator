"""Callable tool library for LLM-based repository agents.

This module exposes a small set of pure(ish) functions intended to be
registered as function-calling / MCP tools for an LLM agent that manages
this repository's GitHub Project (V2) board. Each function:

- Has a fully type-hinted signature and a docstring in Google style, so it
  can be introspected automatically for tool schemas (e.g. via
  ``inspect.signature`` + docstring parsing) or fed to `google-genai`'s
  automatic function calling.
- Talks to GitHub exclusively through the GraphQL ``ProjectV2`` API via
  :class:`GitHubProjectClient`, never the older REST Projects API (deprecated).
- Is side-effect-isolated: network calls live behind ``GitHubProjectClient``
  so this module can be unit-tested with a fake client.

Utility library for GitHub ProjectV2 GraphQL automation.

Environment:
    GITHUB_TOKEN: A token with ``repo`` and ``project`` scopes.
    GITHUB_REPOSITORY: ``owner/name``, injected automatically in Actions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import requests

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

TicketStatus = Literal[
    "status:backlog",
    "status:ready",
    "status:in-progress",
    "status:in-review",
    "status:done",
]


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub GraphQL API returns an error payload."""


@dataclass(frozen=True)
class GitHubProjectClient:
    """Thin GraphQL client scoped to ProjectV2 mutations/queries.

    Attributes:
        token: GitHub personal access token or Actions ``GITHUB_TOKEN``.
        session: Injectable ``requests.Session`` for testability.
    """

    token: str
    session: requests.Session | None = None

    def _session(self) -> requests.Session:
        return self.session or requests.Session()

    def execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Execute a GraphQL query/mutation against the GitHub API.

        Args:
            query: A GraphQL document string.
            variables: GraphQL variables for the document.

        Returns:
            The ``data`` object from the GraphQL response.

        Raises:
            GitHubAPIError: If the response contains an ``errors`` array
                or a non-2xx HTTP status.
        """
        response = self._session().post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        payload = response.json()
        if response.status_code >= 300 or "errors" in payload:
            raise GitHubAPIError(json.dumps(payload.get("errors", payload)))
        return payload["data"]


def load_json_config(filename: str) -> dict[str, Any]:
    """Load a JSON config file from ``git/config``.

    Args:
        filename: Basename of the config file, e.g. ``"project_labels.json"``.

    Returns:
        Parsed JSON content.
    """
    path = CONFIG_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def get_client() -> GitHubProjectClient:
    """Build a :class:`GitHubProjectClient` from the ``GITHUB_TOKEN`` env var.

    Returns:
        A configured client instance.

    Raises:
        RuntimeError: If ``GITHUB_TOKEN`` is not set.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set in the environment")
    return GitHubProjectClient(token=token)


def initialize_ticket(
    repo_owner: str,
    repo_name: str,
    title: str,
    body: str,
    component: str,
    priority: str,
    project_id: str,
    client: GitHubProjectClient | None = None,
) -> dict[str, Any]:
    """Create a GitHub issue and add it to the ProjectV2 board.

    This is the canonical entry point an agent should call when the backlog
    document describes new, unscoped work. It creates the issue, attaches
    the component/priority labels from ``project_labels.json``, then adds
    the resulting node to the target project.

    Args:
        repo_owner: GitHub org or user that owns the repository.
        repo_name: Repository name.
        title: Issue title, ideally mirroring the roadmap bullet text.
        body: Markdown issue body (should include a "Source" link back to
            the roadmap/changelog line it was derived from).
        component: One of the ``component:*`` labels from
            ``project_labels.json``.
        priority: One of the ``priority:*`` labels from
            ``project_labels.json``.
        project_id: The ``ProjectV2`` node ID (not the human-facing number).
        client: Optional injected client for testing.

    Returns:
        A dict with ``issue_id``, ``issue_number``, and ``project_item_id``.
    """
    client = client or get_client()
    labels = _validated_labels(component, priority)

    repo_query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) { id }
    }
    """
    repo_data = client.execute(repo_query, {"owner": repo_owner, "name": repo_name})
    repository_id = repo_data["repository"]["id"]

    create_mutation = """
    mutation($repositoryId: ID!, $title: String!, $body: String!, $labelIds: [ID!]) {
      createIssue(input: {
        repositoryId: $repositoryId, title: $title, body: $body, labelIds: $labelIds
      }) {
        issue { id number }
      }
    }
    """
    label_ids = _resolve_label_ids(client, repo_owner, repo_name, labels)
    created = client.execute(
        create_mutation,
        {
            "repositoryId": repository_id,
            "title": title,
            "body": body,
            "labelIds": label_ids,
        },
    )
    issue = created["createIssue"]["issue"]

    add_to_project_mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
        item { id }
      }
    }
    """
    project_data = client.execute(
        add_to_project_mutation, {"projectId": project_id, "contentId": issue["id"]}
    )

    return {
        "issue_id": issue["id"],
        "issue_number": issue["number"],
        "project_item_id": project_data["addProjectV2ItemById"]["item"]["id"],
    }


def transition_ticket(
    project_id: str,
    item_id: str,
    status_field_id: str,
    status_option_id: str,
    new_status: TicketStatus,
    client: GitHubProjectClient | None = None,
) -> dict[str, Any]:
    """Move a project item to a new single-select status option.

    Callers are expected to have already resolved ``status_field_id`` and
    ``status_option_id`` via :func:`resolve_status_field` -- this function
    performs the mutation only, keeping it a minimal, auditable unit that
    an LLM agent can invoke repeatedly without re-deriving IDs.

    Args:
        project_id: ``ProjectV2`` node ID.
        item_id: ``ProjectV2Item`` node ID for the target ticket.
        status_field_id: Node ID of the "Status" single-select field.
        status_option_id: Node ID of the target option (e.g. "In Progress").
        new_status: Human-readable status label, used only for the return
            payload / logging -- not sent to the API.
        client: Optional injected client for testing.

    Returns:
        A dict confirming the applied ``new_status`` and updated item id.
    """
    client = client or get_client()
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { singleSelectOptionId: $optionId }
      }) {
        projectV2Item { id }
      }
    }
    """
    data = client.execute(
        mutation,
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": status_field_id,
            "optionId": status_option_id,
        },
    )
    return {
        "new_status": new_status,
        "project_item_id": data["updateProjectV2ItemFieldValue"]["projectV2Item"]["id"],
    }


def close_ticket(
    issue_id: str,
    reason: Literal["COMPLETED", "NOT_PLANNED"] = "COMPLETED",
    client: GitHubProjectClient | None = None,
) -> dict[str, Any]:
    """Close a GitHub issue.

    Args:
        issue_id: The issue's GraphQL node ID.
        reason: GitHub's closure reason enum.
        client: Optional injected client for testing.

    Returns:
        A dict with the closed issue's ``state``.
    """
    client = client or get_client()
    mutation = """
    mutation($issueId: ID!, $reason: IssueClosedStateReason!) {
      closeIssue(input: { issueId: $issueId, stateReason: $reason }) {
        issue { state }
      }
    }
    """
    data = client.execute(mutation, {"issueId": issue_id, "reason": reason})
    return {"state": data["closeIssue"]["issue"]["state"]}


def resolve_status_field(
    project_id: str, client: GitHubProjectClient | None = None
) -> dict[str, Any]:
    """Fetch the "Status" single-select field and its option IDs for a project.

    Args:
        project_id: ``ProjectV2`` node ID.
        client: Optional injected client for testing.

    Returns:
        A dict mapping option name -> option node ID, plus the field's own
        node ID under the ``"__field_id__"`` key.
    """
    client = client or get_client()
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name
                options { id name }
              }
            }
          }
        }
      }
    }
    """
    data = client.execute(query, {"projectId": project_id})
    for field in data["node"]["fields"]["nodes"]:
        if field and field.get("name") == "Status":
            result = {opt["name"]: opt["id"] for opt in field["options"]}
            result["__field_id__"] = field["id"]
            return result
    raise GitHubAPIError("No 'Status' single-select field found on project")


def _validated_labels(component: str, priority: str) -> list[str]:
    """Validate a component/priority pair against ``project_labels.json``.

    Args:
        component: A ``component:*`` label name.
        priority: A ``priority:*`` label name.

    Returns:
        ``[component, priority]`` if both are recognized.

    Raises:
        ValueError: If either label is not present in the taxonomy.
    """
    taxonomy = load_json_config("project_labels.json")
    known_components = {item["name"] for item in taxonomy["components"]}
    known_priorities = {item["name"] for item in taxonomy["priority"]}
    if component not in known_components:
        raise ValueError(f"Unknown component label: {component}")
    if priority not in known_priorities:
        raise ValueError(f"Unknown priority label: {priority}")
    return [component, priority]


def _resolve_label_ids(
    client: GitHubProjectClient, owner: str, name: str, label_names: list[str]
) -> list[str]:
    """Resolve label name strings to GraphQL node IDs, creating missing ones.

    Args:
        client: Active GraphQL client.
        owner: Repository owner.
        name: Repository name.
        label_names: Label names to resolve.

    Returns:
        List of label node IDs in the same order as ``label_names``.
    """
    query = """
    query($owner: String!, $name: String!, $labelName: String!) {
      repository(owner: $owner, name: $name) {
        label(name: $labelName) { id }
        id
      }
    }
    """
    label_ids: list[str] = []
    for label_name in label_names:
        data = client.execute(
            query, {"owner": owner, "name": name, "labelName": label_name}
        )
        existing = data["repository"]["label"]
        if existing:
            label_ids.append(existing["id"])
            continue
        label_ids.append(
            _create_label(client, data["repository"]["id"], label_name)
        )
    return label_ids


def _create_label(client: GitHubProjectClient, repository_id: str, label_name: str) -> str:
    """Create a repository label from the taxonomy's configured color.

    Args:
        client: Active GraphQL client.
        repository_id: Repository node ID.
        label_name: Label name to create, must exist in ``project_labels.json``.

    Returns:
        The newly created label's node ID.
    """
    taxonomy = load_json_config("project_labels.json")
    all_labels = [
        entry
        for group in ("components", "priority", "status", "agent")
        for entry in taxonomy[group]
    ]
    match = next(item for item in all_labels if item["name"] == label_name)

    mutation = """
    mutation($repositoryId: ID!, $name: String!, $color: String!, $description: String!) {
      createLabel(input: {
        repositoryId: $repositoryId, name: $name, color: $color, description: $description
      }) {
        label { id }
      }
    }
    """
    data = client.execute(
        mutation,
        {
            "repositoryId": repository_id,
            "name": match["name"],
            "color": match["color"],
            "description": match["description"],
        },
    )
    return data["createLabel"]["label"]["id"]
