# Questraa cleanup audit

## Findings and decisions

### Device legacy Pygame UI

`app/ui/app.py` was the legacy Pygame presentation entry point. The active product entry point is `app.ui_qt.main`, and the Qt package imports the shared controller/router/device/startup services directly. The Pygame screens, components, layout, theme and UI smoke tool were presentation-only; import tracing found no supported runtime, packaging or deployment path that selects them. Their renderer-focused tests were removed. The controller and services remain, and controller behavior assertions continue to run independently of Pygame. `pygame-ce` was removed from both the development extra and the obsolete `pygame-ui` extra.

### Duplicate cloud Qt UI

The cloud `ui_qt/` tree had no supported product/deployment role. `startup-cloud/pyproject.toml` packages `backend*`, `shared*` and `schemas*`, not `ui_qt`; the cloud Dockerfile copies those backend packages and content, while cloud web deployment points to `web`. The cloud-supported architecture is the FastAPI backend plus Next.js web portal. The duplicate Qt files were self-referential; their only test references were two Qt-specific test modules, now retired with the implementation. The device UI remains at `startup/app/ui_qt/` and is the authoritative Raspberry Pi UI. CI no longer provisions PySide6/Qt libraries for the cloud repo.

### Other dead-code checks

- Checked Python imports/runtime references for the Pygame package, QML loaders, deployment inclusions and the cloud duplicate.
- Checked React component references and package declarations. No component or asset met the confidence threshold for safe deletion.
- Checked device release/version metadata consumers before restoring and preserving cloud `backend/pyproject.toml`.
- No migration, content, database, recovery, sync, profile, analytics or assessment path was removed.
- No unproven CLI, deployment hook or dependency was deleted. Web dependencies were not edited.

## Verification limits and outstanding blockers

Windows/Python 3.14 fails to start a local Starlette/Uvicorn test portal: the diagnostic stack blocks in AnyIO's `from_thread.run_blocking_portal` while Windows Proactor creates its self-pipe/socketpair. The device crash/retry integration test is similarly blocked. WSL is denied, Docker is unavailable, and there is no isolated Linux environment here, so those network-service tests could not be validated on Linux.

Web dependency restore could not complete because registry DNS/network access is unavailable; the offline cache is missing `zod-validation-error@4.0.2`. The failed npm attempt left ignored `node_modules` incomplete. Consequently current test/lint/typecheck/build commands cannot launch. A prior Next build reported a build lock; the process list contained no visible Node/Next process and `.next` contained no lock file. No unrelated process was stopped and no lock/cache directory was deleted. Retry with working registry access, then run `npm ci`, web tests, lint, typecheck, build, and browser verification.

See `REPOSITORY_CLEANUP_REPORT.md` for the exact deletion inventory and command results.
