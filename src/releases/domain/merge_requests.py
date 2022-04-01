class MergeRequest:

    class MergeType(str):
        pass
    MergeType.DEV = MergeType('dev')
    MergeType.PROD = MergeType('prod')
    MergeType.MAINTENANCE = MergeType('maintenance')

    def __init__(self, merge_type: MergeType, source_branch: str, target_branch: str):
        self.merge_type = merge_type
        self.source_branch = source_branch
        self.target_branch = target_branch

    def __str__(self):
        return f'{self.merge_type} ({self.source_branch} -> {self.target_branch})'

    def create(self):
        pass
