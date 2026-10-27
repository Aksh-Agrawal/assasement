"""One-shot named fault injector for file-backed integration tests."""


class InjectedCrash(BaseException):
    pass


class FaultInjector:
    def __init__(self) -> None:
        self._armed: str | None = None

    def arm(self, point: str) -> None:
        self._armed = point

    def __call__(self, point: str) -> None:
        if point == self._armed:
            self._armed = None
            raise InjectedCrash(point)
