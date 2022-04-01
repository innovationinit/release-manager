from typing import List

from .commits import Commit


class BranchDifference:
    def __init__(self, commit_log: List[Commit], has_diff: bool):
        self.commit_log = commit_log
        self.has_diff = has_diff
