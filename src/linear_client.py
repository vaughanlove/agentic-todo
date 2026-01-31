"""Linear API client for task management."""

import json
from typing import Any, Dict, List, Optional

import httpx

from .config import LinearConfig
from .error_handler import ErrorSeverity, LinearError
from .utils.logger import get_logger
from .utils.retry import retry_decorator

logger = get_logger(__name__)


class LinearClient:
    """
    Client for interacting with Linear via GraphQL API.
    """

    GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

    def __init__(self, config: LinearConfig, retry_config: dict):
        """
        Initialize Linear client.

        Args:
            config: Linear configuration
            retry_config: Retry configuration dict
        """
        self.config = config
        self.retry_config = retry_config
        self.logger = get_logger(__name__)

        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Authorization": config.api_key or ""
            },
            timeout=30.0
        )

    async def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against Linear API.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Query response data

        Raises:
            LinearError: If query fails
        """
        try:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables

            response = await self.client.post(
                self.GRAPHQL_ENDPOINT,
                json=payload
            )

            if response.status_code != 200:
                raise LinearError(
                    f"Linear API returned status {response.status_code}",
                    severity=ErrorSeverity.HIGH,
                    context={"status_code": response.status_code}
                )

            data = response.json()

            if "errors" in data:
                error_msg = data["errors"][0].get("message", "Unknown error")
                raise LinearError(
                    f"Linear API error: {error_msg}",
                    severity=ErrorSeverity.HIGH,
                    context={"errors": data["errors"]}
                )

            return data.get("data", {})

        except httpx.HTTPError as e:
            raise LinearError(
                f"HTTP error communicating with Linear: {str(e)}",
                severity=ErrorSeverity.HIGH,
                original_error=e
            )
        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Unexpected error in Linear API call: {str(e)}",
                severity=ErrorSeverity.HIGH,
                original_error=e
            )

    @retry_decorator(max_attempts=3, base_delay=1.0, exponential_backoff=True)
    async def create_issue(
        self,
        title: str,
        description: Optional[str] = None,
        priority: int = 0,
        labels: Optional[List[str]] = None,
        assignee_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Linear issue.

        Args:
            title: Issue title
            description: Issue description
            priority: Priority (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)
            labels: List of label IDs
            assignee_id: Assignee user ID
            project_id: Project ID (defaults to configured default)

        Returns:
            Created issue data

        Raises:
            LinearError: If issue creation fails
        """
        try:
            query = """
            mutation IssueCreate($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        title
                        description
                        priority
                        url
                        state {
                            name
                        }
                        team {
                            name
                        }
                    }
                }
            }
            """

            variables = {
                "input": {
                    "title": title,
                    "teamId": self.config.team_id,
                }
            }

            if description:
                variables["input"]["description"] = description

            if priority > 0:
                variables["input"]["priority"] = priority

            if assignee_id:
                variables["input"]["assigneeId"] = assignee_id

            if project_id or self.config.default_project_id:
                variables["input"]["projectId"] = project_id or self.config.default_project_id

            if labels:
                variables["input"]["labelIds"] = labels

            self.logger.info("Creating Linear issue", title=title)

            data = await self._execute_query(query, variables)

            result = data.get("issueCreate", {})

            if not result.get("success"):
                raise LinearError(
                    "Failed to create issue: API returned success=false",
                    severity=ErrorSeverity.HIGH,
                    context={"title": title}
                )

            issue = result.get("issue", {})

            self.logger.info(
                "Issue created successfully",
                issue_id=issue.get("id"),
                identifier=issue.get("identifier"),
                url=issue.get("url")
            )

            return issue

        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Failed to create Linear issue: {str(e)}",
                severity=ErrorSeverity.HIGH,
                original_error=e,
                context={"title": title}
            )

    @retry_decorator(max_attempts=3, base_delay=1.0, exponential_backoff=True)
    async def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        state_id: Optional[str] = None,
        priority: Optional[int] = None,
        labels: Optional[List[str]] = None,
        assignee_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing Linear issue.

        Args:
            issue_id: Issue ID to update
            title: New title
            description: New description
            state_id: New state ID
            priority: New priority
            labels: New label IDs
            assignee_id: New assignee ID

        Returns:
            Updated issue data

        Raises:
            LinearError: If update fails
        """
        try:
            query = """
            mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    success
                    issue {
                        id
                        identifier
                        title
                        description
                        priority
                        url
                        state {
                            name
                        }
                    }
                }
            }
            """

            update_input = {}

            if title is not None:
                update_input["title"] = title
            if description is not None:
                update_input["description"] = description
            if state_id is not None:
                update_input["stateId"] = state_id
            if priority is not None:
                update_input["priority"] = priority
            if labels is not None:
                update_input["labelIds"] = labels
            if assignee_id is not None:
                update_input["assigneeId"] = assignee_id

            variables = {
                "id": issue_id,
                "input": update_input
            }

            self.logger.info("Updating Linear issue", issue_id=issue_id, fields=list(update_input.keys()))

            data = await self._execute_query(query, variables)

            result = data.get("issueUpdate", {})

            if not result.get("success"):
                raise LinearError(
                    "Failed to update issue: API returned success=false",
                    severity=ErrorSeverity.MEDIUM,
                    context={"issue_id": issue_id}
                )

            issue = result.get("issue", {})

            self.logger.info("Issue updated successfully", issue_id=issue_id)

            return issue

        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Failed to update Linear issue: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e,
                context={"issue_id": issue_id}
            )

    @retry_decorator(max_attempts=3, base_delay=1.0, exponential_backoff=True)
    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """
        Get issue details by ID.

        Args:
            issue_id: Issue ID

        Returns:
            Issue data

        Raises:
            LinearError: If fetch fails
        """
        try:
            query = """
            query Issue($id: String!) {
                issue(id: $id) {
                    id
                    identifier
                    title
                    description
                    priority
                    url
                    createdAt
                    updatedAt
                    state {
                        name
                        type
                    }
                    assignee {
                        id
                        name
                    }
                    team {
                        name
                    }
                }
            }
            """

            variables = {"id": issue_id}

            self.logger.info("Fetching Linear issue", issue_id=issue_id)

            data = await self._execute_query(query, variables)

            issue = data.get("issue")

            if not issue:
                raise LinearError(
                    f"Issue not found: {issue_id}",
                    severity=ErrorSeverity.MEDIUM,
                    context={"issue_id": issue_id}
                )

            return issue

        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Failed to get Linear issue: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e,
                context={"issue_id": issue_id}
            )

    @retry_decorator(max_attempts=3, base_delay=1.0, exponential_backoff=True)
    async def list_issues(
        self,
        team_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        state_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List issues with optional filters.

        Args:
            team_id: Filter by team ID
            assignee_id: Filter by assignee ID
            state_id: Filter by state ID
            limit: Maximum number of issues to return

        Returns:
            List of issues

        Raises:
            LinearError: If fetch fails
        """
        try:
            query = """
            query Issues($filter: IssueFilter, $first: Int) {
                issues(filter: $filter, first: $first) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        priority
                        url
                        createdAt
                        updatedAt
                        state {
                            name
                            type
                        }
                        assignee {
                            id
                            name
                        }
                        team {
                            name
                        }
                    }
                }
            }
            """

            filter_obj = {}

            if team_id or self.config.team_id:
                filter_obj["team"] = {"id": {"eq": team_id or self.config.team_id}}

            if assignee_id:
                filter_obj["assignee"] = {"id": {"eq": assignee_id}}

            if state_id:
                filter_obj["state"] = {"id": {"eq": state_id}}

            variables = {
                "filter": filter_obj if filter_obj else None,
                "first": limit
            }

            self.logger.info("Listing Linear issues", filter=filter_obj, limit=limit)

            data = await self._execute_query(query, variables)

            issues = data.get("issues", {}).get("nodes", [])

            self.logger.info(f"Retrieved {len(issues)} issues")

            return issues

        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Failed to list Linear issues: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e
            )

    async def search_issues(self, query: str) -> List[Dict[str, Any]]:
        """
        Search issues by text query.

        Args:
            query: Search query

        Returns:
            List of matching issues

        Raises:
            LinearError: If search fails
        """
        try:
            graphql_query = """
            query SearchIssues($query: String!) {
                issueSearch(query: $query) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        priority
                        url
                        state {
                            name
                            type
                        }
                        team {
                            name
                        }
                    }
                }
            }
            """

            variables = {"query": query}

            self.logger.info("Searching Linear issues", query=query)

            data = await self._execute_query(graphql_query, variables)

            issues = data.get("issueSearch", {}).get("nodes", [])

            self.logger.info(f"Found {len(issues)} issues matching query")

            return issues

        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Failed to search Linear issues: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e,
                context={"query": query}
            )

    async def get_workflow_states(self, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get workflow states for a team.

        Args:
            team_id: Team ID (defaults to configured team)

        Returns:
            List of workflow states

        Raises:
            LinearError: If fetch fails
        """
        try:
            query = """
            query WorkflowStates($teamId: String!) {
                team(id: $teamId) {
                    states {
                        nodes {
                            id
                            name
                            type
                            position
                        }
                    }
                }
            }
            """

            variables = {"teamId": team_id or self.config.team_id}

            data = await self._execute_query(query, variables)

            states = data.get("team", {}).get("states", {}).get("nodes", [])

            return states

        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Failed to get workflow states: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e
            )

    async def mark_issue_complete(self, issue_id: str) -> Dict[str, Any]:
        """
        Mark an issue as complete.

        Args:
            issue_id: Issue ID to complete

        Returns:
            Updated issue data

        Raises:
            LinearError: If update fails
        """
        try:
            # First get workflow states to find "Done" or "Completed"
            states = await self.get_workflow_states()

            completed_state = None
            for state in states:
                if state.get("type") == "completed":
                    completed_state = state
                    break

            if not completed_state:
                raise LinearError(
                    "No completed state found in workflow",
                    severity=ErrorSeverity.MEDIUM,
                    context={"issue_id": issue_id}
                )

            # Update issue to completed state
            return await self.update_issue(
                issue_id=issue_id,
                state_id=completed_state["id"]
            )

        except Exception as e:
            if isinstance(e, LinearError):
                raise
            raise LinearError(
                f"Failed to mark issue as complete: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e,
                context={"issue_id": issue_id}
            )
