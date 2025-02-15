from dataclasses import dataclass


@dataclass
class Repository:
    name: str
    newname: str
    link: str
    description: str
    action: str
