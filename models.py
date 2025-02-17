from dataclasses import dataclass


@dataclass
class BitbucketRepo:
    project: str
    projectname: str
    name: str
    newname: str
    link: str
    description: str
    action: str


@dataclass
class BitbucketProject:
    key: str
    id: int
    name: str
    link: str
    description: str = ""

    def __str__(self) -> str:
        if self.description:
            return f"{self.key} - {self.name} - {self.description}"
        return f"{self.key} - {self.name}"
