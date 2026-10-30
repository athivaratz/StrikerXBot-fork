"""Board file reads and a live host snapshot, without Discord."""

from pathlib import Path

from bot.services.host_info import HostSnapshot, collect, read_board


def test_read_board_strips_a_trailing_null(tmp_path: Path) -> None:
    model = tmp_path / "model"
    model.write_bytes(b"Raspberry Pi 4 Model B\x00")
    missing = tmp_path / "missing"
    assert read_board((model, missing)) == "Raspberry Pi 4 Model B"


def test_read_board_is_none_when_files_are_missing(tmp_path: Path) -> None:
    assert read_board((tmp_path / "a", tmp_path / "b")) is None


def test_read_board_skips_an_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.write_bytes(b"\x00")
    product = tmp_path / "product"
    product.write_text("Board", encoding="utf-8")
    assert read_board((empty, product)) == "Board"


def test_collect_returns_a_snapshot_with_percents_in_range() -> None:
    snapshot = collect()
    assert isinstance(snapshot, HostSnapshot)
    assert 0 <= snapshot.cpu_percent <= 100
    assert 0 <= snapshot.mem_percent <= 100
    assert 0 <= snapshot.disk_percent <= 100
