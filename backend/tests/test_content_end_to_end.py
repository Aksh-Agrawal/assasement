"""Real localhost HTTP content flow with the portable backend database."""

import json
from pathlib import Path

from app.assessment import AssessmentApplication
from app.content.client import ContentApiClient
from app.content.sync import ContentSyncStatus, sync_content_once
from app.core.models import Profile
from app.data.repo import Repository
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.content import publish_pack_bytes
from backend.tests.conftest import TOKEN, issue_test_credential
from backend.tests.test_end_to_end import LocalUvicorn


def test_real_local_publish_download_upgrade_and_resume(tmp_path: Path) -> None:
    storage = tmp_path / "server-content"
    backend_url = f"sqlite:///{(tmp_path / 'backend-content.db').as_posix()}"
    application = create_app(
        Settings(database_url=backend_url, content_storage_path=storage)
    )
    server = LocalUvicorn(application)
    server.start()
    try:
        issue_test_credential(application)
        v1 = Path("content/sample_biology.json").read_bytes()
        v2_value = json.loads(v1)
        v2_value["set"]["version"] = 2
        v2_value["questions"][0]["question_text"] = "Local HTTP version 2"
        v2 = json.dumps(v2_value, ensure_ascii=False, separators=(",", ":")).encode()
        with application.state.session_factory() as session:
            publish_pack_bytes(v1, session=session, storage_root=storage)

        database = tmp_path / "device.db"
        with Repository(database) as repository:
            with ContentApiClient(server.base_url, auth_token=TOKEN) as client:
                first = sync_content_once(
                    repository,
                    client,
                    temp_directory=tmp_path / "downloads",
                    max_pack_bytes=25 * 1024 * 1024,
                    max_downloads_per_cycle=5,
                )
            assert first.packs[0].status is ContentSyncStatus.INSTALLED
            student = repository.create_profile(Profile("student-1", "Student"))
            assessment = AssessmentApplication(repository)
            attempt = assessment.start_test(student.id, "biology-cell-practice-01", 1)
            order = repository.get_attempt_question_order(attempt.id)
            assessment.select_answer("A")

            with application.state.session_factory() as session:
                publish_pack_bytes(v2, session=session, storage_root=storage)
            with ContentApiClient(server.base_url, auth_token=TOKEN) as client:
                second = sync_content_once(
                    repository,
                    client,
                    temp_directory=tmp_path / "downloads",
                    max_pack_bytes=25 * 1024 * 1024,
                    max_downloads_per_cycle=5,
                )
            assert any(item.status is ContentSyncStatus.INSTALLED for item in second.packs)
            assert repository.get_active_question_set("biology-cell-practice-01").version == 2

        with Repository(database) as repository:
            resumed = AssessmentApplication(repository).resume_attempt(student.id)
            assert resumed is not None and resumed.set_version == 1
            assert repository.get_attempt_question_order(attempt.id) == order
            newer = repository.create_profile(Profile("student-2", "Student 2"))
            next_attempt = AssessmentApplication(repository).start_test(
                newer.id, "biology-cell-practice-01", 2
            )
            assert next_attempt.set_version == 2
    finally:
        server.stop()
