class RateLimited(BaseException):
    def __init__(self, retry_after: float, *args: object) -> None:
        super().__init__(*args)
        self.retry_after = retry_after
