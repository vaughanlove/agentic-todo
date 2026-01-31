#!/usr/bin/env python3
"""Quick script to fetch Linear workspace and team IDs."""

import os
import sys
import json
import urllib.request

# Get API key from environment
api_key = os.getenv('LINEAR_API_KEY')

if not api_key:
    print("Error: LINEAR_API_KEY not set")
    print("Run: export LINEAR_API_KEY=your_key_here")
    sys.exit(1)

# GraphQL query to get viewer info
query = """
query {
  viewer {
    id
    name
    email
    organization {
      id
      name
      urlKey
    }
  }
  teams {
    nodes {
      id
      name
      key
    }
  }
}
"""

# Make request
url = "https://api.linear.app/graphql"
headers = {
    "Content-Type": "application/json",
    "Authorization": api_key
}

data = json.dumps({"query": query}).encode('utf-8')

try:
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))

    if 'errors' in result:
        print("Error from Linear API:")
        print(json.dumps(result['errors'], indent=2))
        sys.exit(1)

    data = result.get('data', {})

    # Print organization info
    org = data.get('viewer', {}).get('organization', {})
    print("\n" + "="*60)
    print("LINEAR WORKSPACE INFORMATION")
    print("="*60)
    print(f"\nOrganization: {org.get('name', 'N/A')}")
    print(f"Workspace ID: {org.get('urlKey', 'N/A')}")
    print(f"Organization UUID: {org.get('id', 'N/A')}")

    # Print teams
    teams = data.get('teams', {}).get('nodes', [])
    print("\n" + "="*60)
    print("TEAMS")
    print("="*60)

    if teams:
        for team in teams:
            print(f"\nTeam: {team.get('name', 'N/A')}")
            print(f"  Key: {team.get('key', 'N/A')}")
            print(f"  ID: {team.get('id', 'N/A')}")
    else:
        print("\nNo teams found")

    # Print config snippet
    print("\n" + "="*60)
    print("ADD TO config.yaml:")
    print("="*60)
    print("\nlinear:")
    print(f"  workspace_id: \"{org.get('urlKey', 'your-workspace-id')}\"")
    if teams:
        print(f"  team_id: \"{teams[0].get('id', 'your-team-id')}\"")
    else:
        print(f"  team_id: \"your-team-id\"")
    print()

except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode('utf-8'))
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
