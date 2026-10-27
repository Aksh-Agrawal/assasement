"""Raspberry Pi GPIO button diagnostic; created but not hardware-verified."""

import signal
import threading

from app.input.actions import Action
from app.input.buttons import ButtonHardwareUnavailable, ButtonInput

STATUS = "CREATED BUT NOT HARDWARE-VERIFIED"


def main() -> int:
    print(f"GPIO button diagnostic - STATUS: {STATUS}")
    print("BCM numbering; internal pull-ups; active LOW; 40 ms software debounce.")

    def report(action: Action) -> None:
        label = action.value.removeprefix("SELECT_")
        print(f"{label} pressed", flush=True)

    buttons = ButtonInput(report)
    try:
        buttons.start()
    except ButtonHardwareUnavailable as error:
        print(f"UNAVAILABLE: {error}")
        return 2

    stopped = threading.Event()

    def stop(_signum: int, _frame: object) -> None:
        stopped.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print("Press each physical button. Press Ctrl+C to stop.")
    try:
        stopped.wait()
    finally:
        buttons.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
