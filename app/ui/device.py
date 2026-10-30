"""Device-console service adapter. Background work owns a separate repository.

Only immutable results cross into the event loop; a network call never blocks
assessment navigation or borrows its SQLite connection.
"""

import shutil
import threading
import time
from concurrent.futures import Future
from pathlib import Path

import httpx
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from app.api.client import DeviceApi
from app.api.transport import failure_state
from app.auth.credentials import CredentialStore
from app.auth.profile_links import ProfileLinkError
from app.config import AppConfig
from app.content.sync import _install_one
from app.data.repo import Repository
from app.diagnostics import collect_device_status, collect_network_status
from app.sync.service import run_cycle
from app.system.wifi import WifiService
from app.update.activation import ActivationManager
from app.update.staging import stage_update
from app.update.verifier import verify_update
from tools.create_support_bundle import create_support_bundle


class DeviceConsole:
    def __init__(self, database_path: Path, config=None, credentials=None):
        self.database_path = database_path
        self.config = config or AppConfig(database_path=database_path)
        self.credentials = credentials or CredentialStore(
            self.config.credential_path if database_path == self.config.database_path
            else database_path.parent / "device_credentials.json"
        )
        self.wifi = WifiService()
        self.future = None
        self.operation = ""
        self.message = ""
        self.failure = None
        self.link_error = None
        self.link_result = None
        self.network = None
        self.network_checked_at = 0.0
        self.account_verified = False
        self.wifi_connected = False
        self.internet_status = "Unknown"
        self.diagnostics = None
        self.networks = ()
        self.saved_networks = ()
        self.catalog = ()
        self.catalog_profile_id = None
        self.pairing = None
        self.available_update = None
        self.staged = None
        self.download_state = {}
        self.generation = 0
        self.pairing_lock = threading.Lock()

    def cancel_pairing(self):
        with self.pairing_lock:
            self.generation += 1
            self.pairing = None

    @property
    def busy(self):
        return self.future is not None

    def start(self, operation, **arguments):
        if self.busy:
            self.message = "A device action is still running. Assessment remains available."
            return
        remote = {
            "account_sync", "account_create", "account_disconnect",
            "sync",
            "catalog",
            "download",
            "update_check",
            "update_download",
            "pair_request",
            "pair_poll",
            "profile_claim", "profile_unlink", "profile_status", "institute_refresh", "institute_download",
        }
        if operation in remote and not self.config.api_base_url:
            self.message = ("Network unavailable. Local assessment remains available." if operation.startswith("profile_")
                            else "Server not configured. Local assessment remains available.")
            return
        if operation in remote - {"pair_request", "pair_poll"} and not self.credentials.load_safe():
            self.message = (
                "Device authentication required. Pair this device; local assessment remains available."
                if operation.startswith("profile_") else "Authentication required. Pair this device; local assessment remains available."
            )
            return
        self.link_error = None
        self.account_message = None
        self.operation = operation
        self.message = {
            "profile_claim": "Submitting link...",
            "profile_unlink": "Unlinking profile...",
            "profile_status": "Checking link status...",
            "download": "Downloading and validating question pack...",
            "update_download": "Downloading, verifying and staging update...",
            "diagnostics": "Checking local device...",
            "sync": "Syncing completed assessments...",
        }.get(operation, "Working...")
        self.future = Future()
        future = self.future
        generation = self.generation

        def work():
            try:
                result = self._execute(operation, generation=generation, **arguments)
                future.set_result((generation, result))
            except ProfileLinkError as error:
                self.link_error = error.code
                future.set_exception(error)
            except Exception as error:
                self.failure = failure_state(error)
                if operation.startswith("account_"):
                    if isinstance(error, httpx.RequestError):
                        self.account_message = "Connect to the internet to create a new profile." if operation == "account_create" else "Network unavailable. Cached study profiles remain usable offline."
                    elif isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 409:
                        self.account_message = "Profile limit reached: 3 / 3 active Study Profiles. Archive a profile on the website first."
                    elif isinstance(error, httpx.HTTPStatusError) and error.response.status_code in {401, 403}:
                        self.account_message = "This device is no longer connected. Reconnect from Account & Devices. Assessment data is retained."
                # Network errors, OS diagnostics, and URLs never become user-facing text.
                future.set_exception(
                    RuntimeError(
                        "Action unavailable. Check connection or device configuration and retry."
                    )
                )

        threading.Thread(target=work, daemon=True, name="device-console").start()

    def poll(self):
        if self.future is None or not self.future.done():
            return False
        future, self.future = self.future, None
        try:
            generation, value = future.result()
            if generation != self.generation:
                self.message = "Pairing cancelled."
                return True
            op = self.operation
            if op in {"account_sync", "account_create"}:
                self.account_verified = True
            elif op == "account_disconnect":
                self.account_verified = False
            if op in {"profile_claim", "profile_unlink", "profile_status"}:
                self.link_result = value
                self.message = (
                    "Linked to account: " + value["account_display_name"] +
                    " / Study profile: " + value["study_profile_name"]
                    if value["status"] == "linked" else
                    "Profile unlinked. Local data and historical ownership are preserved."
                )
                return True
            if op == "diagnostics":
                self.diagnostics = value
            elif op == "network":
                self.wifi_connected, self.network, self.internet_status = value
                self.network_checked_at = time.monotonic()
                self.message = (
                    f"Internet: {self.internet_status}. Cloud: "
                    + ("not checked" if not self.network.checked else
                       "unreachable" if not self.network.backend_reachable else
                       "ready" if self.network.database_ready else "reachable, not ready")
                    + ". Local assessment remains available."
                )
                return True
            elif op == "wifi_scan":
                self.saved_networks, self.networks = value
            elif op in {"wifi_connect", "wifi_forget"}:
                self.wifi_connected = bool(value)
                self.network = None
            elif op == "catalog":
                self.catalog_profile_id, self.catalog = value
            elif op == "pair_request":
                self.pairing = value
            elif op == "pair_poll":
                if value in {"approved", "expired", "consumed", "denied", "unavailable"}:
                    self.pairing = None
                self.message = (
                    "Paired successfully." if value == "approved" else f"Pairing: {value}."
                )
                return True
            elif op == "update_check":
                self.available_update = value
            elif op == "update_download":
                self.staged = value
            elif op in {"download", "institute_download"}:
                self.download_state[(value.set_id, value.version)] = value.status.value
                self.message = {
                    "INSTALLED": "Downloaded and verified.",
                    "ALREADY_PRESENT": "Downloaded.",
                }.get(value.status.value, "Downloaded content is available offline." if value.status.value == "ALREADY_PRESENT"
                      else "Validation or download failed. Retry available.")
                return True
            elif op == "sync":
                self.message = (
                    "Authentication required."
                    if value.authentication_failures
                    else "Sync attention required. Data retained; ask your operator."
                    if value.permanent_failures
                    else "Failed - retry available."
                    if value.transient_failures
                    else "Up to date."
                    if value.selected == 0
                    else f"Synced {value.synced + value.already_synced} assessments."
                )
                return True
            elif op == "export":
                self.message = f"Support bundle saved: {value.name}"
                return True
            self.message = (
                "Ready."
                if op not in {"wifi_connect", "wifi_forget"}
                else "Network action completed. Check internet separately."
            )
        except ProfileLinkError as error:
            self.message = str(error)
        except Exception:
            self.message = getattr(self, "account_message", None) or "Action unavailable. Check connection or device configuration and retry."
        return True

    def _execute(self, operation, **args):
        config = self.config
        if operation in {"account_sync", "account_create", "account_disconnect"}:
            from app.auth.account_device import sync_account
            with Repository(self.database_path) as repository:
                return sync_account(config, self.credentials, repository,
                    create=args.get("create"), disconnect=operation == "account_disconnect")
        if operation in {"profile_claim", "profile_unlink", "profile_status"}:
            with Repository(self.database_path) as repository:
                profile = repository.get_profile(args["local_profile_id"])
                if profile is None:
                    raise ProfileLinkError("LINK_PROFILE_CONFLICT")
                if operation == "profile_claim" and profile.link_state == "linked":
                    raise ProfileLinkError("LINK_PROFILE_CONFLICT")
                with DeviceApi(config, store=self.credentials).profile_links() as client:
                    if operation == "profile_claim":
                        result = client.claim(args["code"], profile.id)
                    elif operation == "profile_unlink":
                        context = repository.get_profile_link_context(profile.id)
                        if context is None:
                            raise ProfileLinkError("LINK_PROFILE_CONFLICT")
                        result = client.unlink(profile.id, context["link_id"])
                    else:
                        result = client.current(profile.id)
                if result["status"] != "unlinked":
                    repository.apply_profile_link(profile.id, result)
                return result
        if operation == "wifi_scan":
            return self.wifi.saved(), self.wifi.scan()
        if operation == "wifi_connect":
            self.wifi.connect(**args)
            return self.wifi.connected()
        if operation == "wifi_forget":
            self.wifi.forget(args["name"])
            return self.wifi.connected()
        if operation == "export":
            return create_support_bundle(
                database_path=self.database_path,
                credential_path=self.credentials.path,
                log_directory=config.log_directory,
                update_root=config.update_root,
                output_directory=self.database_path.parent / "support",
                trusted_key_id=config.trusted_update_key_id,
            )
        if operation in {"pair_request", "pair_poll"}:
            if not config.api_base_url:
                raise RuntimeError("API not configured")
            with DeviceApi(config, store=self.credentials).pairing() as client:
                if operation == "pair_request":
                    return client.request(args["device_id"], "Assessment Device")
                state = client.status(args["pairing"])
                if state == "approved":
                    console = self

                    class GuardedStore:
                        def save(self, credential):
                            with console.pairing_lock:
                                if console.generation == args.get("generation", console.generation):
                                    console.credentials.save(credential)

                    client.claim(args["pairing"], GuardedStore(), args["device_id"])
                return (
                    state
                    if state in {"pending", "approved", "expired", "consumed", "denied"}
                    else "unavailable"
                )
        credential = self.credentials.load_safe()
        token = credential.token if credential else None
        if operation == "network":
            try:
                connected = self.wifi.connected()
            except (OSError, RuntimeError):
                connected = False
            try:
                internet = self.wifi.internet_status()
            except (OSError, RuntimeError):
                internet = "Unknown"
            return connected, collect_network_status(
                config.api_base_url, auth_token=token, connect_timeout=2, read_timeout=3
            ), internet
        with Repository(self.database_path) as repository:
            if operation == "diagnostics":
                return collect_device_status(
                    repository,
                    database_path=self.database_path,
                    credential_store=self.credentials,
                    update_manager=ActivationManager(config.update_root),
                    trusted_signing_key_id=config.trusted_update_key_id,
                )
            if not config.api_base_url:
                raise RuntimeError("API not configured")
            if operation == "sync":
                from dataclasses import replace

                return run_cycle(replace(config, database_path=self.database_path,
                                         credential_path=self.credentials.path), refresh=True)
            if operation in {"institute_refresh", "institute_download"}:
                from app.content.institute_work import download_work, refresh_work
                profile_id = args["local_profile_id"]
                context = repository.get_profile_link_context(profile_id)
                if not context:
                    raise RuntimeError("Link profile first")
                with DeviceApi(config, store=self.credentials).institute_content(
                    local_profile_id=profile_id, link_id=context["link_id"]) as client:
                    if operation == "institute_refresh":
                        return refresh_work(repository, client, profile_id, context["link_id"])
                    return download_work(repository, client, profile_id, context["link_id"], args["assignment_id"],
                        temp_directory=config.content_download_directory, max_pack_bytes=config.content_max_pack_bytes)
            if operation in {"catalog", "download"}:
                profile_id = args.get("local_profile_id")
                profile = repository.get_profile(profile_id) if profile_id else None
                context = repository.get_profile_link_context(profile_id) if profile_id else None
                scoped = bool(profile and profile.ownership_state == "owned")
                if scoped and (profile.link_state != "linked" or not context):
                    raise RuntimeError("Link the study profile before refreshing its library")
                options = {"local_profile_id": profile_id, "link_id": context["link_id"]} if scoped else {}
                with DeviceApi(config, store=self.credentials).content(**options) as client:
                    if operation == "catalog":
                        if scoped:
                            from app.content.profile_library import refresh_library
                            return profile_id, refresh_library(repository, client, profile_id, context["link_id"])
                        return None, client.fetch_catalog().packs
                    if scoped:
                        from app.content.profile_library import download_for_profile
                        return download_for_profile(
                            repository, client, profile_id, context["link_id"], args["pack"],
                            temp_directory=config.content_download_directory,
                            max_pack_bytes=config.content_max_pack_bytes,
                        )
                    return _install_one(
                        repository, client, args["pack"],
                        temp_directory=config.content_download_directory,
                        max_pack_bytes=config.content_max_pack_bytes,
                    )
            if operation in {"update_check", "update_download"}:
                if not token:
                    raise RuntimeError("Pairing required")
                client = DeviceApi(config, store=self.credentials).updates()
                try:
                    if operation == "update_check":
                        return client.check_for_update()
                    update = args["update"]
                    # Pin the filename locally. Never accept a server path.
                    filename = update.manifest.data["artifact"]["filename"]
                    if Path(filename).name != filename or "/" in filename or "\\" in filename:
                        raise ValueError("Unsafe artifact filename")
                    artifact = client.download_update(
                        update, config.update_root / "downloads" / filename
                    )
                    key = load_pem_public_key(config.trusted_update_public_key_path.read_bytes())
                    verified = verify_update(
                        update.manifest_bytes,
                        update.signature,
                        artifact,
                        trusted_keys={config.trusted_update_key_id: key},
                        current_version=config.application_version,
                        platform=config.update_platform,
                        architecture=config.update_architecture,
                        db_schema=repository.schema_version,
                    )
                    return stage_update(verified, config.update_root)
                finally:
                    client.close()
        raise ValueError("Unsupported device action")

    def device_rows(self, repository):
        root = self.database_path.resolve().parent
        return (
            ("Software", self.config.application_version),
            ("Device", "Assessment Device"),
            (
                "Assessment storage",
                "Available offline",
            ),
            ("Question packs", str(len(repository.list_question_sets()))),
            ("Free storage", f"{shutil.disk_usage(root).free / 2**30:.1f} GB"),
        )
