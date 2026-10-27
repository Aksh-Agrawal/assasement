"""Offline verifier for explicitly encoded PBKDF2 PINs; unknown formats fail closed.

The original repository only stored opaque PIN columns. This adapter never treats
an unrecognised hash as an unprotected profile and never rewrites existing hashes.
"""

import hashlib
import hmac
import time

from app.data.repo import Repository


class PinUnlock:
    def __init__(self, repository: Repository, *, clock=time.time):
        self.repository = repository
        self.clock = clock

    def protected(self, profile_id: str) -> bool:
        digest, salt = self.repository.get_profile_pin(profile_id)
        return bool(digest or salt)

    def unlock(self, profile_id: str, pin: str) -> tuple[bool, str]:
        key = f"pin_lock:{profile_id}"
        until = float(self.repository.get_setting(key) or 0)
        if self.clock() < until:
            return False, "PIN locked temporarily. Please wait before retrying."
        digest, salt = self.repository.get_profile_pin(profile_id)
        try:
            algorithm, rounds, expected = (digest or "").split("$")
            if algorithm != "pbkdf2_sha256" or not salt or not 100_000 <= int(rounds) <= 1_000_000:
                raise ValueError
            actual = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), int(rounds)).hex()
        except (ValueError, TypeError):
            return False, "This profile needs account recovery. Existing PIN data is preserved."
        if hmac.compare_digest(actual, expected):
            self.repository.delete_setting(key)
            self.repository.delete_setting(key + ":failures")
            return True, ""
        failures = int(self.repository.get_setting(key + ":failures") or 0) + 1
        self.repository.set_setting(key + ":failures", str(failures))
        if failures >= 5:
            self.repository.set_setting(
                key, str(self.clock() + min(900, 30 * 2 ** min(5, failures - 5)))
            )
        return False, "Incorrect PIN. Please try again."
