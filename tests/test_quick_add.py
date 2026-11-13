"""Unit and integration tests for QR Mobile Quick Add on Raspberry Pi."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Ensure headless offscreen platform for Qt testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from app.auth.credentials import CredentialStore, DeviceCredential
from app.config import AppConfig
from app.sync.mobile_upload import (
    MobileSessionInfo,
    MobileSessionStatus,
    MobileUploadAuthError,
    MobileUploadClient,
)
from app.ui_qt.controllers.app_controller import AppController
from app.ui_qt.controllers.quick_add_controller import QuickAddController


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


@pytest.fixture
def mock_credentials(tmp_path):
    cred_file = tmp_path / "device_credentials.json"
    store = CredentialStore(cred_file)
    store.save(
        DeviceCredential(
            device_id="test-pi-01",
            token="dev-tok-12345",
        )
    )
    return store


@pytest.fixture
def mock_config(tmp_path):
    return AppConfig(
        database_path=tmp_path / "app.db",
        credential_path=tmp_path / "device_credentials.json",
        api_base_url="https://cloud.test",
    )


class TestMobileUploadClient:
    def test_create_session_success(self, mock_config, mock_credentials):
        client = MobileUploadClient("https://cloud.test", auth_token="dev-tok-12345")
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_resp.is_success = True
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {
            "session_id": "sess-1234",
            "token": "tok-abc",
            "upload_url": "https://test.edu/quick-add/tok-abc",
            "short_code": "AB7K-2QF",
            "expires_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
            "status": "WAITING_FOR_PHONE",
            "profile_name": "Alex",
        }

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            info = client.create_session("prof-01")

        assert isinstance(info, MobileSessionInfo)
        assert info.session_id == "sess-1234"
        assert info.token == "tok-abc"
        assert info.upload_url == "https://test.edu/quick-add/tok-abc"
        assert info.short_code == "AB7K-2QF"
        assert info.profile_name == "Alex"
        mock_post.assert_called_once()

    def test_create_session_auth_error(self, mock_config, mock_credentials):
        client = MobileUploadClient("https://cloud.test", auth_token="dev-tok-12345")
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.is_success = False
        mock_resp.text = "Unauthorized device"

        with patch.object(client._client, "post", return_value=mock_resp):
            with pytest.raises(MobileUploadAuthError):
                client.create_session("prof-01")

    def test_get_status_success(self, mock_config, mock_credentials):
        client = MobileUploadClient("https://cloud.test", auth_token="dev-tok-12345")
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {
            "session_id": "sess-1234",
            "status": "READY",
            "expires_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
            "result_set_id": "pack-xyz",
            "pack_title": "Cell Biology",
            "question_count": 5,
            "error_code": None,
            "error_message": None,
        }

        with patch.object(client._client, "get", return_value=mock_resp):
            st = client.get_status("sess-1234")

        assert isinstance(st, MobileSessionStatus)
        assert st.status == "READY"
        assert st.result_set_id == "pack-xyz"
        assert st.pack_title == "Cell Biology"
        assert st.question_count == 5


class TestQuickAddController:
    def test_initial_state(self, qapp, tmp_path, mock_config, mock_credentials):
        mock_app = Mock(spec=AppController)
        mock_app.database_path = tmp_path / "app.db"
        mock_app.config = mock_config
        mock_app.credentials = mock_credentials

        controller = QuickAddController(mock_app)
        assert controller.status == "WAITING_FOR_PHONE"
        assert controller.remainingTime == "10:00"
        assert controller.shortCode == ""
        assert controller.packTitle == ""

    def test_handle_server_status_transitions(self, qapp, tmp_path, mock_config, mock_credentials):
        mock_app = Mock(spec=AppController)
        mock_app.database_path = tmp_path / "app.db"
        mock_app.config = mock_config
        mock_app.credentials = mock_credentials

        controller = QuickAddController(mock_app)
        controller._session_id = "sess-123"
        expires = datetime.now(UTC) + timedelta(minutes=10)

        # Phone connected
        st = MobileSessionStatus(
            session_id="sess-123",
            status="PHONE_CONNECTED",
            expires_at=expires,
            result_set_id=None,
            pack_title=None,
            question_count=None,
            error_code=None,
            error_message=None,
        )
        controller._handle_server_status("PHONE_CONNECTED", st)
        assert controller.status == "PHONE_CONNECTED"

        # Uploading
        st = MobileSessionStatus(
            session_id="sess-123",
            status="UPLOADING",
            expires_at=expires,
            result_set_id=None,
            pack_title=None,
            question_count=None,
            error_code=None,
            error_message=None,
        )
        controller._handle_server_status("UPLOADING", st)
        assert controller.status == "UPLOADING"

        # Processing
        st = MobileSessionStatus(
            session_id="sess-123",
            status="PROCESSING",
            expires_at=expires,
            result_set_id=None,
            pack_title=None,
            question_count=None,
            error_code=None,
            error_message=None,
        )
        controller._handle_server_status("PROCESSING", st)
        assert controller.status == "PROCESSING"

        # Needs review
        st = MobileSessionStatus(
            session_id="sess-123",
            status="NEEDS_REVIEW",
            expires_at=expires,
            result_set_id=None,
            pack_title=None,
            question_count=None,
            error_code=None,
            error_message=None,
        )
        controller._handle_server_status("NEEDS_REVIEW", st)
        assert controller.status == "NEEDS_REVIEW"

        # Expired
        st = MobileSessionStatus(
            session_id="sess-123",
            status="EXPIRED",
            expires_at=expires,
            result_set_id=None,
            pack_title=None,
            question_count=None,
            error_code=None,
            error_message=None,
        )
        controller._handle_server_status("EXPIRED", st)
        assert controller.status == "EXPIRED"

        # Failed
        st = MobileSessionStatus(
            session_id="sess-123",
            status="FAILED",
            expires_at=expires,
            result_set_id=None,
            pack_title=None,
            question_count=None,
            error_code="PARSE_ERROR",
            error_message="Scanned PDF not supported",
        )
        controller._handle_server_status("FAILED", st)
        assert controller.status == "FAILED"
        assert "Scanned PDF" in controller.errorMessage

    def test_controller_uses_backend_provided_url_and_entry_url(self, qapp, tmp_path, mock_config, mock_credentials):
        mock_app = Mock(spec=AppController)
        mock_app.database_path = tmp_path / "app.db"
        mock_app.config = mock_config
        mock_app.credentials = mock_credentials

        controller = QuickAddController(mock_app)
        expires = datetime.now(UTC) + timedelta(minutes=10)
        prod_url = "https://startup-cloud-1.onrender.com/quick-add/demo-token-xyz"

        controller._on_session_created("sess-1", "demo-token-xyz", prod_url, "TEST-CODE", expires, "Alex")

        assert controller.uploadUrl == prod_url
        assert controller.entryUrl == "startup-cloud-1.onrender.com/quick-add"

    def test_sync_finished_ready_state(self, qapp, tmp_path, mock_config, mock_credentials):
        mock_app = Mock(spec=AppController)
        mock_app.database_path = tmp_path / "app.db"
        mock_app.config = mock_config
        mock_app.credentials = mock_credentials
        mock_app.ui_controller = Mock()

        controller = QuickAddController(mock_app)
        controller._status = "SYNCING_TO_DEVICE"
        controller._sync_in_progress = True
        controller._pack_title = "Physics 101"
        controller._question_count = 10

        controller._on_sync_finished(pack_present=True)

        assert controller.status == "READY"
        assert controller.statusText == "Ready to practice!"
        assert controller._sync_in_progress is False
        mock_app.ui_controller.refresh_catalog.assert_called_once()

    def test_cancel_quick_add(self, qapp, tmp_path, mock_config, mock_credentials):
        mock_app = Mock(spec=AppController)
        mock_app.database_path = tmp_path / "app.db"
        mock_app.config = mock_config
        mock_app.credentials = mock_credentials

        controller = QuickAddController(mock_app)
        controller._session_id = "sess-123"

        with patch("app.ui_qt.controllers.quick_add_controller.DeviceApi"):
            controller.cancelQuickAdd()

        assert controller.status == "CANCELLED"
        mock_app.navigate.assert_called_with("content")


class TestQuickAddQML:
    def test_qml_quick_add_screen_load(self, qapp, tmp_path, mock_config, mock_credentials):
        engine = QQmlApplicationEngine()
        qml_dir = Path(__file__).resolve().parent.parent / "app" / "ui_qt" / "qml"
        engine.addImportPath(str(qml_dir))

        mock_app = Mock(spec=AppController)
        mock_app.database_path = tmp_path / "app.db"
        mock_app.config = mock_config
        mock_app.credentials = mock_credentials
        mock_app.screen = "quick_add"
        mock_app.activeProfileName = "Alex"
        mock_app.networkLabel = "Online"
        mock_app.syncLabel = "Idle"
        mock_app.isOnline = True

        controller = QuickAddController(mock_app)
        controller._status = "WAITING_FOR_PHONE"
        controller._short_code = "AB7K-2QF"

        root_context = engine.rootContext()
        root_context.setContextProperty("appController", mock_app)
        root_context.setContextProperty("quickAddController", controller)

        screen_qml = qml_dir / "screens" / "QuickAddScreen.qml"
        engine.load(QUrl.fromLocalFile(str(screen_qml)))

        assert len(engine.rootObjects()) > 0
