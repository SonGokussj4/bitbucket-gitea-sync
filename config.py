from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"

    BITBUCKET_URL: str = ""
    BITBUCKET_PROJECT: str = ""
    BITBUCKET_USERNAME: str = ""
    BITBUCKET_PASSWORD: str = ""
    BITBUCKET_TOKEN: str = ""

    GITEA_URL: str = ""
    GITEA_API_URL: str = ""
    GITEA_TOKEN: str = ""
    GITEA_USERNAME: str = ""
    GITEA_USER_ID: str = "1"
    GITEA_ORGANIZATION: str = ""
    GITEA_SET_AS_MIRROR: bool = False

    ORG_PREFIX: str = ""

    AZURE_DEVOPS_URL: str = ""
    AZURE_DEVOPS_ORGANIZATION: str = ""
    AZURE_DEVOPS_PROJECT: str = ""
    AZURE_DEVOPS_TOKEN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
