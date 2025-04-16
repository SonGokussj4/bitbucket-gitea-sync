import csv
import os
from dataclasses import dataclass
from pathlib import Path

import niquests
from niquests.auth import HTTPBasicAuth

from config import settings
from log_config import logger
from models import BitbucketProject, BitbucketRepo

# API endpoint for listing repositories
BITBUCKET_PROJECTS_API_URL = f"{settings.BITBUCKET_URL}/rest/api/1.0/projects"
BITBUCKET_REPOS_API_URL = f"{settings.BITBUCKET_URL}/rest/api/1.0/projects/{settings.BITBUCKET_PROJECT}/repos"

CSV_FILENAME = "bitbucket_repos.csv"


def list_projects() -> list[BitbucketProject]:
    """
    List all projects in Bitbucket.
    """
    auth = HTTPBasicAuth(settings.BITBUCKET_USERNAME, settings.BITBUCKET_PASSWORD)
    project_list: list[BitbucketProject] = []
    start = 0
    is_last_page = False

    # Using Niquests' Session with multiplexing enabled for improved performance
    with niquests.Session(multiplexed=True) as session:
        while not is_last_page:
            response = session.get(f"{BITBUCKET_PROJECTS_API_URL}?start={start}", auth=auth, verify=True)  # type: ignore
            if response.status_code == 200:
                data = response.json()
                projects = data["values"]
                for project in projects:
                    bitbucket_project = BitbucketProject(
                        key=project["key"],
                        id=project["id"],
                        name=project["name"],
                        description=project.get("description", "") or "",
                        link=project["links"]["self"][0]["href"],
                    )
                    project_list.append(bitbucket_project)
                    # logger.info(f"Project: {bitbucket_project.key}, Name: {bitbucket_project.name} - {bitbucket_project.description}")
                    logger.info(bitbucket_project)

                is_last_page = data["isLastPage"]
                if not is_last_page:
                    start = data["nextPageStart"]
            else:
                logger.error(f"Failed to list projects: {response.status_code} - {response.text}")
                break

    return project_list


def list_repositories(project: BitbucketProject) -> list[BitbucketRepo]:
    """
    List all repositories for the specified Bitbucket project, handling pagination.
    """

    if not project:
        logger.error("Project / Project Name is required.")
        return []

    logger.info(f"Listing repositories for project: {project.key}")
    BITBUCKET_REPOS_API_URL = f"{settings.BITBUCKET_URL}/rest/api/1.0/projects/{project.key}/repos"

    auth = HTTPBasicAuth(settings.BITBUCKET_USERNAME, settings.BITBUCKET_PASSWORD)
    repo_list: list[BitbucketRepo] = []
    start = 0
    is_last_page = False

    # Using Niquests' Session with multiplexing enabled for improved performance
    with niquests.Session(multiplexed=True) as session:
        while not is_last_page:
            response = session.get(f"{BITBUCKET_REPOS_API_URL}?start={start}", auth=auth, verify=True)  # type: ignore
            if response.status_code == 200:
                data = response.json()
                repos = data["values"]
                for repo in repos:
                    clone_links = repo["links"]["clone"]
                    http_link = next(link["href"] for link in clone_links if link["name"] == "http")
                    org_prefix = f"{settings.ORG_PREFIX}-" if settings.ORG_PREFIX else ""
                    repo_info = BitbucketRepo(
                        project=f"{org_prefix}{project.key}",
                        projectname=project.name,
                        name=repo["name"],
                        newname="",  # Placeholder for the new name
                        link=http_link,
                        description=repo.get("description", "").replace("\r\n", " ").replace("\n", " ").replace(",", ";"),
                        action="",  # Placeholder for the action to take
                    )
                    repo_list.append(repo_info)
                    logger.info(f"Repository: {repo_info.name}, Link: {repo_info.link}, Description: {repo_info.description}")

                is_last_page = data["isLastPage"]
                if not is_last_page:
                    start = data["nextPageStart"]
            else:
                logger.error(f"Failed to list repositories: {response.status_code} - {response.text}")
                break

    return repo_list


repository_actions: dict[str, list[str]] = {
    "Archive": [
        "my-repo1",
        "my-repo2",
    ],
    "Ignore": [
        "my-ignored-repo1",
        "my-ignored-repo2",
    ],
    "Move": [
        "my-moved-repo1",
        "my-moved-repo2",
    ],
}


def write_csv(data: list[BitbucketRepo], prefix: str = "", mode: str = "w"):
    """
    Write the list of repositories to a CSV file.
    """

    if "-" not in prefix and prefix:
        prefix = f"{prefix}-"

    file_exists = os.path.exists(CSV_FILENAME) and os.path.getsize(CSV_FILENAME) > 0

    # Open file in append or write mode
    with open(CSV_FILENAME, mode, newline="") as f:
        writer = csv.writer(f)

        # Write header only if the file is empty and we're not in append mode
        if not file_exists or mode == "w":
            writer.writerow(["project", "projectname", "name", "newname", "link", "description", "action"])

        for repo in data:
            # Determine the action to take based on the repository name, if name is not found, default to "Move"
            try:
                action = next(action for action, repos in repository_actions.items() if repo.name in repos)
            except StopIteration:
                action = "Move"

            # Clean up the repository name
            new_name = repo.name.replace("aiis", "ais").replace("_", "-")

            # Active repository names should start with "ais-"
            if action == "Move":
                # new_name = f"{prefix}{new_name.replace('ais-', '')}"
                new_name = f"{prefix}{new_name}"
                logger.info(f"Moving repository: {repo.name} to {new_name}")

            elif action == "Ignore":
                logger.info(f"Ignoring repository: {repo.name}")
                continue  # Skip ignored repositories

            elif action == "Archive":
                new_name = f"zArchive-ais-{new_name.replace('ais-', '')}"
                logger.info(f"Archiving repository: {repo.name}")

            new_name = new_name.lower().replace(" ", "-").replace("_", "-").replace(".", "-").replace("(", "").replace(")", "")

            # Write repository details to CSV
            writer.writerow([repo.project, repo.projectname, repo.name, new_name, repo.link, repo.description, action])

    # Sort the file properly after all projects have been processed
    if mode == "w" or not file_exists:  # Only sort once at the end
        with open(CSV_FILENAME, "r", newline="") as f:
            data = list(csv.DictReader(f))
            data.sort(key=lambda x: (x["newname"], x["name"]))

        with open(CSV_FILENAME, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["project", "projectname", "name", "newname", "link", "description", "action"])
            writer.writeheader()
            writer.writerows(data)


if __name__ == "__main__":
    projects = list_projects()

    for project in projects:
        logger.info(project)

    if Path(CSV_FILENAME).exists():
        Path(CSV_FILENAME).unlink()

    for project in projects:
        repositories = list_repositories(project)
        write_csv(repositories, "", mode="a")

    exit()
