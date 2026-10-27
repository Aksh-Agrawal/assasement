"""Interactive terminal diagnostic for canonical keyboard actions."""

from app.input.keyboard import KeyboardInput


def main() -> int:
    keyboard = KeyboardInput()
    print("Keyboard input diagnostic")
    print("Enter key names (a, 1, left, enter, escape, s, n, g, r); q exits.")
    while True:
        try:
            key = input("\nEnter key/action: ")
        except EOFError:
            print("Diagnostic closed.")
            return 0
        if key.strip().casefold() in {"q", "quit", "exit"}:
            print("Diagnostic closed.")
            return 0
        action = keyboard.translate(key)
        print(f"Emitted: {action.value}" if action else "Emitted: NONE (unknown key)")


if __name__ == "__main__":
    raise SystemExit(main())
