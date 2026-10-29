"""Profile linking transport. Short codes and student secrets are never persisted."""
from uuid import UUID

import httpx

from app.api.transport import create_client

MESSAGES = {
    "LINK_INVALID": "Invalid code",
    "LINK_EXPIRED": "Code expired",
    "LINK_CONSUMED": "Already used",
    "LINK_CANCELLED": "Code cancelled",
    "LINK_PROFILE_CONFLICT": "Profile already linked",
    "LINK_OWNERSHIP_MISMATCH": "Profile ownership does not match",
    "LINK_DEVICE_UNAUTHENTICATED": "Device authentication required",
    "LINK_NETWORK": "Could not link profile. Check your connection and try again.",
    "LINK_SERVER": "Server unavailable. Try again.",
}


class ProfileLinkError(RuntimeError):
    def __init__(self, code):
        self.code = code if code in MESSAGES else "LINK_SERVER"
        super().__init__(MESSAGES[self.code])


class ProfileLinkClient:
    def __init__(self, base_url, *, auth_token=None, transport=None,
                 connect_timeout=5.0, read_timeout=15.0):
        self.authenticated = bool(auth_token)
        self.client = create_client(base_url, auth_token=auth_token, transport=transport,
                                    connect_timeout=connect_timeout, read_timeout=read_timeout)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.client.close()

    def _request(self, method, path, **kwargs):
        if not self.authenticated:
            raise ProfileLinkError("LINK_DEVICE_UNAUTHENTICATED")
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.RequestError:
            raise ProfileLinkError("LINK_NETWORK") from None
        if response.status_code == 401:
            raise ProfileLinkError("LINK_DEVICE_UNAUTHENTICATED")
        if not response.is_success:
            try:
                code = response.json()["detail"]["code"]
            except (ValueError, KeyError, TypeError):
                code = "LINK_SERVER"
            raise ProfileLinkError(code)
        try:
            data = response.json()
            if data["status"] == "unlinked":
                return data
            if data["status"] not in {"linked", "revoked"}:
                raise ValueError()
            for key in ("link_id", "student_account_id", "study_profile_id"):
                UUID(data[key])
            for key in ("local_profile_id", "account_display_name", "study_profile_name"):
                if not isinstance(data[key], str) or not data[key]:
                    raise ValueError()
            return data
        except (ValueError, KeyError, TypeError):
            raise ProfileLinkError("LINK_SERVER") from None

    def claim(self, code, local_profile_id):
        return self._request("POST", "/api/v1/profile-links/claim",
                             json={"code": code, "local_profile_id": local_profile_id})

    def current(self, local_profile_id):
        return self._request("GET", "/api/v1/profile-links/current",
                             params={"local_profile_id": local_profile_id})

    def unlink(self, local_profile_id, link_id):
        return self._request("POST", "/api/v1/profile-links/unlink",
                             json={"local_profile_id": local_profile_id, "link_id": link_id})
