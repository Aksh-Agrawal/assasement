"""Publish a validated immutable question pack to the development backend."""

import argparse
from pathlib import Path

from backend.app.config import Settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.services.content import PackVersionConflict, publish_pack_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    args = parser.parse_args()
    settings = Settings.from_environment()
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            result = publish_pack_file(
                args.pack,
                session=session,
                storage_root=settings.content_storage_path,
            )
    except PackVersionConflict as error:
        parser.error(str(error))
    finally:
        engine.dispose()
    state = "published" if result.created else "already published"
    print(
        f"{result.pack.set_id} v{result.pack.version}: {state} "
        f"({result.pack.size_bytes} bytes, sha256={result.pack.sha256})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
