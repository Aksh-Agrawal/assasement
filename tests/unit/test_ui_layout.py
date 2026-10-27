"""Framework-neutral layout coverage for future touch reliability."""

from app.ui.layout import LOGICAL_HEIGHT, LOGICAL_WIDTH, Rect, scale_point, wrap_text


def test_rect_hit_testing_inside_outside_and_boundaries() -> None:
    rect = Rect(10, 20, 100, 48)
    assert rect.contains((10, 20))
    assert rect.contains((109.999, 67.999))
    assert not rect.contains((9.999, 20))
    assert not rect.contains((110, 20))
    assert not rect.contains((10, 68))


def test_scale_point_converts_window_to_logical_coordinates() -> None:
    assert scale_point((800, 480), (1600, 960)) == (
        LOGICAL_WIDTH / 2,
        LOGICAL_HEIGHT / 2,
    )


def test_wrap_text_handles_short_long_and_unicode_content() -> None:
    def measure(value: str) -> int:
        return len(value) * 10

    assert wrap_text("short text", measure, 200) == ["short text"]
    assert wrap_text("one two three four", measure, 90) == ["one two", "three", "four"]
    assert wrap_text("Na⁺ and Cl⁻ form ionic compounds", measure, 110, max_lines=2) == [
        "Na⁺ and Cl⁻",
        "form ionic…",
    ]
    assert wrap_text("deoxyribonucleicacid", measure, 50) == [
        "deoxy",
        "ribon",
        "uclei",
        "cacid",
    ]
