"""DEVELOPMENT / TEST ONLY: revoke a device and all active credentials."""

import argparse
from datetime import UTC, datetime
from uuid import UUID

from backend.app.config import Settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.services.pairing import revoke_device


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device_id", type=UUID)
    args = parser.parse_args()
    settings = Settings.from_environment()
    engine = create_database_engine(settings.database_url)
    try:
        with create_session_factory(engine)() as session:
            if not revoke_device(session, args.device_id, now=datetime.now(UTC)):
                raise SystemExit("Device not found")
    finally:
        engine.dispose()
    print("Device revoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
