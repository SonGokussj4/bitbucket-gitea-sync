# bitbucket-gitea-sync

Migration and later syncing of batch bitbucket repos to gitea

## Requirements

- uv <https://docs.astral.sh/uv/getting-started/installation/>

## Configuration

```bash
cp .env.example .env
```

- Fill in the `.env` file with your Bitbucket and Gitea credentials

## Run

### Export all repos from bitbucket to a `bitbucket_repos.csv` file

```bash
uv run bitbucket_repos.py
```

> *OPTIONAL: Modify the `bitbucket_repos.csv` file to remove any repos you don't want to import to gitea*

### Import all repos from the `bitbucket_repos.csv` file to gitea

```bash
uv run gitea_repos.py
```
