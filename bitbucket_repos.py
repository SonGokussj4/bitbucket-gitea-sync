import csv

import niquests
from niquests.auth import HTTPBasicAuth

from config import settings
from log_config import logger
from models import Repository

# API endpoint for listing repositories
BITBUCKET_PROJECTS_API_URL = f"{settings.BITBUCKET_URL}/rest/api/1.0/projects"
BITBUCKET_REPOS_API_URL = f"{settings.BITBUCKET_URL}/rest/api/1.0/projects/{settings.BITBUCKET_PROJECT}/repos"


def list_repositories() -> list[Repository]:
    """
    List all repositories for the specified Bitbucket project, handling pagination.
    """
    auth = HTTPBasicAuth(settings.BITBUCKET_USERNAME, settings.BITBUCKET_PASSWORD)
    repo_list: list[Repository] = []
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
                    repo_info = Repository(
                        name=repo["name"],
                        newname="",  # Placeholder for the new name
                        link=http_link,
                        description=repo.get("description", "").replace("\r\n", " ").replace("\n", " ").replace(",", ";"),
                        action="",  # Placeholder for the action to take
                    )
                    repo_list.append(repo_info)
                    logger.debug(f"Repository: {repo_info.name}, Link: {repo_info.link}, Description: {repo_info.description}")

                is_last_page = data["isLastPage"]
                if not is_last_page:
                    start = data["nextPageStart"]
            else:
                logger.error(f"Failed to list repositories: {response.status_code} - {response.text}")
                break

    return repo_list


repository_actions: dict[str, list[str]] = {
    "Archive": [
        "ada_cermat",
        "ada-makro",
        "ada-tacr",
        "box_defect_detector_model",
        "detection_and_classification",
        "mlp-amper-demo",
        "mlp-demo-diton",
        "mlp-functionality-mobilenetv2",
        "mlp-liberec-demo",
        "mlp-mobilebox-bits-demo",
        "object_measurement",
        "software-triggering",
        "st_micro",
    ],
    "Ignore": [
        "AI-Studio-postgres",
        "ada-jenkins-library",
        "ada-releases",
        "ada_resource",
        "ada-slack-webhook",
        "ADNet",
        "automatic_labeler",
        "azure-gpu",
        "build-scripts",
        "calibtool",
        "cvat-deploy",
        "deploy-traefik-configurations",
        "logger",
        "mlp-demo-template",
        "mlp-demo-websocket-liveview",
        "mlp-dxp",
        "mlp-functionality-hello-world",
        "ml_platform_service-aiis",
        "mlp-model-template",
        "ml-showcase",
        "ml-training-app-alt",
        "ml-training-mock-api",
        "monitoring",
        "rd-brn-ml-05",
        "status-scrapper",
        "vqi-bdd-usecase",
        "vtts_region_classification",
        "vtts_test_data",
    ],
    "Move": [
        "ada-modeling",
        "aiis_core",
        "aiis_sam",
        "aiis_task_manager",
        "aiis_vas_integration",
        "ais-ansible",
        "ais_data_proxy",
        "ais-docker",
        "ais_streamer",
        "ais-stats",
        "anomalib",
        "diton-qr",
        "ffmpeg-openh264",
        "gui-tests",
        "infra",
        "mlflow",
        "mlinipekare",
        "mlp-backend-base",
        "mlp-backend-tfs",
        "mlp-backend-torchserve",
        "mlp-connector-base",
        "mlp-connector-genicam",
        "mlp-connector-influxdb",
        "mlp-connector-mobotix",
        "mlp-connector-rtsp",
        "mlp-connector-websocket",
        "mlp-functionality-base",
        "mlp-functionality-datasaver",
        "mlp-functionality-ump",
        "mlp-functionality-vtts",
        "ml_platform_service",
        "mlp_resize_plugin",
        "mlp-torchserving",
        "ml-training-app",
        "mobotix-pylib",
        "nvidia-checker",
        "rtsp-recorder",
        "small-httpd",
        "vqi_center_net",
        "vtts_anomaly_detection",
        "WT901C485",
    ],
}

if __name__ == "__main__":
    repositories = list_repositories()

    # Save the repos into a csv file with headers: Name, Link, Description, Action
    with open("bitbucket_repos.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "newname", "link", "description", "action"])
        for repo in repositories:
            # Determine the action to take based on the repository name
            action = next(action for action, repos in repository_actions.items() if repo.name in repos)

            # Clean up the repository name
            new_name = repo.name.replace("aiis", "ais").replace("_", "-")

            # Active repository names should start with "ais-"
            if action == "Move":
                new_name = f"ais-{new_name.replace('ais-', '')}"
                logger.info(f"Moving repository: {repo.name} to {new_name}")

            # This repository will be ignored, not archived or moved
            elif action == "Ignore":
                logger.info(f"Ignoring repository: {repo.name}")
                continue

            # This repository will be archived (zArchive- prefix)
            elif action == "Archive":
                new_name = f"zArchive-ais-{new_name.replace('ais-', '')}"
                logger.info(f"Archiving repository: {repo.name}")

            # Write the repository details to the csv file
            writer.writerow([repo.name, new_name, repo.link, repo.description, action])

    # Sort the bitbucket_repos.csv file by the NewName and Name columns
    with open("bitbucket_repos.csv", "r", newline="") as f:
        data = list(csv.DictReader(f))
        data.sort(key=lambda x: (x["newname"], x["name"]))

    with open("bitbucket_repos.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
