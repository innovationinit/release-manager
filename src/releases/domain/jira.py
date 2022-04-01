from typing import List


class JiraIssue:
    def __init__(self, key: str, summary: str, labels: List[str]):
        self.key = key
        self.summary = summary
        self.labels = labels
