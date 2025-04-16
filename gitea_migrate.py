import csv
from pathlib import Path
from typing import Any

import niquests
from loguru import logger
from niquests.auth import HTTPBasicAuth

from bitbucket_repos import list_repositories
from config import settings
from models import BitbucketRepo

# API endpoint for repository migrations
GITEA_MIGRATE_API_URL = f"{settings.GITEA_API_URL}/repos/migrate"
GITEA_DELETE_API_URL = f"{settings.GITEA_API_URL}/repos"
GITEA_DELETE_ORG_API_URL = f"{settings.GITEA_API_URL}/orgs"

# CSV file containing the repository details
CURDIR = Path(__file__).resolve().parent
CSV_REPOSITORIES = CURDIR / "bitbucket_repos.csv"  # Replace with the path to your CSV file

DELETE_EXISTING_REPOS = False

HEADERS = {
    "Authorization": f"token {settings.GITEA_TOKEN}",
    "Content-Type": "application/json",
    "accept": "application/json",
}

_existing_org: list[str] = []


# def delete_existing_repo(repo_name: str, session: niquests.Session):
#     """
#     Delete an existing repository in Gitea if it exists.
#     """
#     delete_url = f"{GITEA_DELETE_API_URL}/{settings.GITEA_ORGANIZATION}/{repo_name}"
#     headers = {"Authorization": f"token {settings.GITEA_TOKEN}"}

#     response = session.delete(delete_url, headers=headers, verify=False)  # type: ignore
#     if response.status_code == 204:
#         logger.success(f"Successfully deleted existing repository: {repo_name}")
#     elif response.status_code == 404:
#         logger.info(f"Repository '{repo_name}' does not exist. Skipping deletion.")
#     else:
#         logger.error(f"Failed to delete repository '{repo_name}': {response.status_code} - {response.text}")


# def sync_existing_repo(repo_name: str, session: niquests.Session):
#     """
#     Sync an existing mirrored repository in Gitea to fetch the latest updates.
#     """
#     sync_url = f"{settings.GITEA_URL}/api/v1/repos/{settings.GITEA_ORGANIZATION}/{repo_name}/mirror-sync"
#     headers = {"Authorization": f"token {settings.GITEA_TOKEN}"}

#     response = session.post(sync_url, headers=headers, verify=False)  # type: ignore
#     if response.status_code == 200:
#         logger.success(f"Successfully synced repository: {repo_name}")
#     elif response.status_code == 404:
#         logger.warning(f"Repository '{repo_name}' does not exist. Skipping sync.")
#     else:
#         logger.error(f"Failed to sync repository '{repo_name}': {response.status_code} - {response.text}")


# def update_repo_mirror_status(repo_name: str, session: niquests.Session, mirror_status: bool):
#     """
#     Update an existing repository in Gitea to be a mirror or non-mirror based on the mirror_status.
#     """
#     repo_url = f"{settings.GITEA_URL}/api/v1/repos/{settings.GITEA_ORGANIZATION}/{repo_name}"
#     headers = {"Authorization": f"token {settings.GITEA_TOKEN}"}

#     response = session.get(repo_url, headers=headers, verify=False)  # type: ignore
#     if response.status_code == 200:
#         repo_data = response.json()
#         status_str = "non-mirror"
#         if repo_data.get("mirror", False) != mirror_status:
#             status_str = "mirror" if mirror_status else "non-mirror"
#             logger.info(f"Repository '{repo_name}' is not a {status_str}. Updating to {status_str}...")
#             update_payload = {"mirror": mirror_status}
#             update_response = session.patch(repo_url, json=update_payload, headers=headers, verify=False)  # type: ignore
#             if update_response.status_code == 200:
#                 logger.success(f"Successfully updated repository '{repo_name}' to be a {status_str}.")
#                 if mirror_status:
#                     sync_existing_repo(repo_name, session)
#             else:
#                 logger.error(
#                     f"Failed to update repository '{repo_name}' to be a {status_str}: {update_response.status_code} - {update_response.text}"
#                 )
#         else:
#             logger.info(f"Repository '{repo_name}' is already a {status_str}.")
#     else:
#         logger.error(f"Failed to fetch repository '{repo_name}' details: {response.status_code} - {response.text}")


# def create_or_update_repo(repo_name: str, repo_link: str, session: niquests.Session, mirror_status: bool):
#     """
#     Handle repository creation or update if it exists.
#     """
#     payload = build_payload(repo_name, repo_link, mirror_status)
#     payload_clean = payload.copy()
#     payload_clean["clone_addr"] = repo_link

#     logger.info(f"Setting up repository: {repo_name} from {repo_link}... {payload_clean}")
#     response = session.post(GITEA_MIGRATE_API_URL, json=payload, headers=HEADERS, verify=False)  # type: ignore

#     if response.status_code == 201:
#         logger.success(f"Successfully set up repository: {repo_name}")
#     elif response.status_code == 409:
#         logger.info(f"Repository '{repo_name}' already exists. Attempting to sync...")
#         sync_existing_repo(repo_name, session)
#     else:
#         logger.error(f"Failed to migrate {repo_name}: {response.status_code} - {response.json()}")


def build_payload(repo: BitbucketRepo) -> dict[str, Any]:
    """
    Build the payload to migrate or update a repository in Gitea.
    """
    auth_clone_url = repo.link.replace("https://", f"https://{settings.BITBUCKET_USERNAME}:{settings.BITBUCKET_PASSWORD}@")
    payload: dict[str, Any] = {
        "repo_name": repo.newname,
        "clone_addr": auth_clone_url,
        "repo_owner": repo.project,
        "description": repo.description,
        "mirror": settings.GITEA_SET_AS_MIRROR,
        "private": False,
        "releases": True,
        "pull_requests": True,
        "lfs": True,
        # "issues": True,
    }
    return payload


def process_repository(repo: BitbucketRepo, session: niquests.Session):
    """
    1. Check if the repo.project (organization) exists in Gitea. If not, create it.
    2. Check if the repo.newname (repository) exists in the organization.
        - If not, create a mirror from Bitbucket.
        - If it exists, update it from the original Bitbucket repo.
    """
    global _existing_org

    # Step 1: Check if the organization exists
    if repo.project not in _existing_org:
        org_url = f"{settings.GITEA_API_URL}/orgs/{repo.project}"
        org_response = session.get(org_url, headers=HEADERS)  # type: ignore

        if org_response.status_code == 404:
            logger.info(f"Organization '{repo.project}' not found in Gitea. Creating it...")
            org_data = {
                "username": repo.project,
                "full_name": repo.projectname,
                "description": repo.description,
                "visibility": "public",
            }
            create_org_response = session.post(  # type: ignore
                f"{settings.GITEA_API_URL}/orgs",
                headers=HEADERS,
                json=org_data,
                verify=False,
            )
            if create_org_response.status_code == 201:
                logger.success(f"Organization '{repo.project}' created successfully.")
                # Write globally that this organization has been created for future faster checks
                _existing_org.append(repo.project)
            else:
                logger.error(f"Failed to create organization '{repo.project}': {create_org_response.text}")
                return
        else:
            logger.debug(f"Organization '{repo.project}' already exists in Gitea.")

    # Step 2: Check if the repository exists
    repo_url = f"{settings.GITEA_API_URL}/repos/{repo.project}/{repo.newname}"
    repo_response = session.get(repo_url, headers=HEADERS)  # type: ignore

    if not repo_response.status_code == 404 and not DELETE_EXISTING_REPOS:
        logger.info(f"Repository '{repo.newname}' already exists in Gitea. Ignoring it...")
        return

    payload = build_payload(repo)

    # Clone the repository from Bitbucketaa
    try:
        if DELETE_EXISTING_REPOS:
            logger.info(f"Deleting existing repository: {repo.newname}...")
            delete_repo(repo.project, repo.newname)

        # Migrate the repository
        logger.info(f"Migrating repository: {repo.newname} from {repo.link}... {payload}")
        response = session.post(GITEA_MIGRATE_API_URL, json=payload, headers=HEADERS, verify=False, timeout=1800)  # type: ignore

    except niquests.exceptions.Timeout:
        logger.error(f"Timeout error while setting up repository: {repo.newname}")
        try:
            delete_repo(repo.project, repo.newname)
        except niquests.exceptions.RequestException as e:
            logger.error(f"Error while setting up repository: {repo.newname} - {e}")
        return
    except niquests.exceptions.RequestException as e:
        logger.error(f"Error while setting up repository: {repo.newname} - {e}")
        try:
            delete_repo(repo.project, repo.newname)
        except niquests.exceptions.RequestException as e:
            logger.error(f"Error while setting up repository: {repo.newname} - {e}")
        return

    if response.status_code == 201:
        logger.success(f"Successfully set up repository: {repo.newname}")
    else:
        logger.error(f"Error: {response.text}")
        logger.error(f"Failed to migrate {repo.newname}: {response.status_code} - {response.json()}")


def migrate_repositories(csv_file: Path):
    # Get the repositories from the CSV file
    with open(csv_file, "r", newline="") as f:
        data = list(csv.DictReader(f))
        repositories = [BitbucketRepo(**row) for row in data]

    total_repos = len(repositories)
    for idx, repo in enumerate(repositories):
        logger.info(f"{idx + 1}/{total_repos} Migrating: {repo.project} - {repo.name} - {repo.link}")
        process_repository(repo, niquests.Session())


def import_to_azure_devops(repositories: list[BitbucketRepo]):
    # Azure DevOps organization and project details
    organization = settings.AZURE_DEVOPS_ORGANIZATION
    project = settings.AZURE_DEVOPS_PROJECT
    pat = settings.AZURE_DEVOPS_TOKEN

    # Azure DevOps REST API base URL
    base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories"

    # # Test if I can reach the DevAzure API endpoint with my token
    # url = settings.AZURE_DEVOPS_URL
    # Headers for the HTTP requests
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # TEST
    response = niquests.get(base_url, headers=headers)  # type: ignore
    if response.status_code == 203:
        logger.success("Successfully connected to Azure DevOps")
    else:
        logger.error("Failed to connect to Azure DevOps")

    def create_repository(repo_name: str):
        url = f"{base_url}?api-version=7.1"

        def get_project_id(project_name):
            url = f"https://dev.azure.com/{organization}/_apis/projects/{project_name}?api-version=7.1"
            response = niquests.get(url, headers=headers, auth=HTTPBasicAuth("", pat))
            if response.status_code == 200:
                return response.json()["id"]
            else:
                print(f"Failed to retrieve project ID for '{project_name}'. Status Code: {response.status_code}, Message: {response.text}")
                return None

        project_id = get_project_id(project)

        payload = {"name": repo_name, "project": {"id": project_id}}  # type: ignore
        response = niquests.post(url, json=payload, headers=headers, auth=HTTPBasicAuth("", pat))  # type: ignore
        if response.status_code == 201:
            print(f"Repository '{repo_name}' created successfully.")
            return response.json()["id"]
        elif response.status_code == 409:
            print(f"Repository '{repo_name}' already exists.")
            # Retrieve the existing repository ID
            repo_id = get_repository_id(repo_name)
            return repo_id
        else:
            print(f"Failed to create repository '{repo_name}'. Status Code: {response.status_code}, Message: {response.text}")
            return None

    # Function to get the repository ID by name
    def get_repository_id(repo_name: str):
        url = f"{base_url}/{repo_name}?api-version=7.1"
        response = niquests.get(url, headers=headers, auth=HTTPBasicAuth("", pat))  # type: ignore
        if response.status_code == 200:
            return response.json()["id"]
        else:
            print(f"Failed to retrieve repository ID for '{repo_name}'. Status Code: {response.status_code}, Message: {response.text}")
            return None

    # Function to import a repository from an external Git source
    def import_repository(repo_id: str, source_url: str, username: str, password: str):
        url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/importRequests?api-version=7.1"
        payload = {"parameters": {"gitSource": {"url": source_url, "username": username, "password": password}}}
        response = niquests.post(url, json=payload, headers=headers, auth=HTTPBasicAuth("", pat))  # type: ignore
        if response.status_code == 201:
            logger.success(f"Import request for repository ID '{repo_id}' created successfully.")
        else:
            logger.error(
                f"Failed to create import request for repository ID '{repo_id}'. Status Code: {response.status_code}, Message: {response.text}"
            )

    # Read the CSV file and process each repository
    with open(CSV_REPOSITORIES, mode="r") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            repo_name = row["newname"]
            source_url = row["link"]
            # Step 1: Create the repository in Azure DevOps
            logger.info(f"Processing repository: '{repo_name}' from '{source_url}'")

            logger.info(f"Create repository: '{repo_name}'")
            # repo_id = create_repository(repo_name)
            repo_id = get_repository_id(repo_name)
            logger.info(f"Repository ID: {repo_id}")
            if repo_id:
                # Step 2: Import the repository from the source URL
                import_repository(repo_id, source_url, settings.BITBUCKET_USERNAME, settings.BITBUCKET_PASSWORD)


def delete_orgs(orgs: list[str]):
    for org in orgs:
        delete_url = f"{GITEA_DELETE_ORG_API_URL}/{org}"
        response = niquests.delete(delete_url, headers=HEADERS, verify=False)  # type: ignore
        if response.status_code == 204:
            logger.success(f"Successfully deleted existing org: {org}")
        elif response.status_code == 404:
            logger.info(f"Org '{org}' does not exist. Skipping deletion.")
        else:
            logger.error(f"Failed to delete org '{org}': {response.status_code} - {response.text}")


def delete_repo(org: str, repo: str):
    delete_url = f"{GITEA_DELETE_API_URL}/{org}/{repo}"
    response = niquests.delete(delete_url, headers=HEADERS, verify=False)  # type: ignore
    if response.status_code == 204:
        logger.success(f"Successfully deleted existing repository: {repo}")
    elif response.status_code == 404:
        logger.info(f"Repository '{repo}' does not exist. Skipping deletion.")
    else:
        logger.error(f"Failed to delete repository '{repo}': {response.status_code} - {response.text}")


def delete_all_repos_in_org(org: str):
    repos = niquests.get(f"{GITEA_DELETE_ORG_API_URL}/{org}/repos", headers=HEADERS, verify=False)  # type: ignore
    if repos.status_code == 200:
        for repo in repos.json():
            delete_repo(org, repo["name"])
    else:
        logger.error(f"Failed to list repositories: {repos.status_code} - {repos.text}")


# Run the migration
if __name__ == "__main__":
    # orgs = [
    #     # "Konica-DI",
    #     # "Konica-DOB",
    #     # "Konica-CSI",
    #     # "Konica-EBRN1",
    #     # "Konica-BLUE",
    #     # "Konica-AD",
    #     # "Konica-AP",
    #     # "Konica-AIP",
    #     # "Konica-AL",
    #     # "Konica-ALDN",
    #     "Konica-DMOC",
    # ]
    # for org in orgs:
    #     delete_all_repos_in_org(org)
    # delete_orgs(orgs)

    migrate_repositories(CSV_REPOSITORIES)
