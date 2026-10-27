"""DEVELOPMENT / TEST ONLY: approve a pending pairing code."""

import argparse
from datetime import UTC, datetime

from backend.app.config import Settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.services.pairing import PairingRejected, approve_pairing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code")
    args = parser.parse_args()
    settings = Settings.from_environment()
    engine = create_database_engine(settings.database_url)
    try:
        with create_session_factory(engine)() as session:
            approve_pairing(session, args.code, now=datetime.now(UTC))
    except PairingRejected as error:
        raise SystemExit(str(error)) from error
    finally:
        engine.dispose()
    print("Pairing approved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
