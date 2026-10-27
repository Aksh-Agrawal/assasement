"""Actionable update failure categories."""


class UpdateError(RuntimeError):
    pass


class ManifestError(UpdateError):
    pass


class SignatureError(UpdateError):
    pass


class IntegrityError(UpdateError):
    pass


class CompatibilityError(UpdateError):
    pass


class StagingError(UpdateError):
    pass
