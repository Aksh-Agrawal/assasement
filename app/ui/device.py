"""Device-console service adapter. Background work owns a separate repository.

Only immutable results cross into the event loop; a network call never blocks
assessment navigation or borrows its SQLite connection.
"""

import platform
import shutil
import threading
from concurrent.futures import Future
from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_pem_public_key

from app.api.client import DeviceApi
from app.api.transport import failure_state
from app.auth.credentials import CredentialStore
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
        self.network = None
        self.wifi_connected = False
        self.diagnostics = None
        self.networks = ()
        self.saved_networks = ()
        self.catalog = ()
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
            "sync",
            "catalog",
            "download",
            "update_check",
            "update_download",
            "pair_request",
            "pair_poll",
        }
        if operation in remote and not self.config.api_base_url:
            self.message = "Server not configured. Local assessment remains available."
            return
        if operation in remote - {"pair_request", "pair_poll"} and not self.credentials.load_safe():
            self.message = (
                "Authentication required. Pair this device; local assessment remains available."
            )
            return
        self.operation = operation
        self.message = {
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
            except Exception as error:
                self.failure = failure_state(error)
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
            if op == "diagnostics":
                self.diagnostics = value
            elif op == "network":
                self.wifi_connected, self.network = value
                self.message = (
                    "Internet available."
                    if self.network.backend_reachable
                    else "Internet unavailable. Local assessment remains available."
                )
                return True
            elif op == "wifi_scan":
                self.saved_networks, self.networks = value
            elif op in {"wifi_connect", "wifi_forget"}:
                self.wifi_connected = bool(value)
                self.network = None
            elif op == "catalog":
                self.catalog = value
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
            elif op == "download":
                self.download_state[(value.set_id, value.version)] = value.status.value
                self.message = {
                    "INSTALLED": "Downloaded and verified.",
                    "ALREADY_PRESENT": "Downloaded.",
                }.get(value.status.value, "Validation or download failed. Retry available.")
                return True
            elif op == "sync":
                self.message = (
                    "Authentication required."
                    if value.authentication_failures
                    else "Failed - retry available."
                    if value.transient_failures or value.permanent_failures
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
        except Exception:
            self.message = "Action unavailable. Check connection or device configuration and retry."
        return True

    def _execute(self, operation, **args):
        config = self.config
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
            return connected, collect_network_status(
                config.api_base_url, auth_token=token, connect_timeout=2, read_timeout=3
            )
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
            if operation in {"catalog", "download"}:
                with DeviceApi(config, store=self.credentials).content() as client:
                    if operation == "catalog":
                        return client.fetch_catalog().packs
                    return _install_one(
                        repository,
                        client,
                        args["pack"],
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
            ("Device", repository.get_or_create_device_id()[:8]),
            ("Platform", platform.system()),
            ("Architecture", platform.machine()),
            (
                "Database",
                self.diagnostics.local_db_status if self.diagnostics else "Run diagnostics",
            ),
            ("Question packs", str(len(repository.list_question_sets()))),
            ("Free storage", f"{shutil.disk_usage(root).free / 2**30:.1f} GB"),
        )
