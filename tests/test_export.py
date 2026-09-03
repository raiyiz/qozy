import numpy as np

from qozy.core.export import day_folder, next_file_number, save_measurement


def test_day_folder_creates_dated_path(tmp_path) -> None:
    folder = day_folder(tmp_path)
    assert folder.exists()
    assert folder.is_relative_to(tmp_path)


def test_next_file_number_finds_first_free_slot(tmp_path) -> None:
    folder = day_folder(tmp_path)
    (folder / "01.txt").write_text("x")
    assert next_file_number(folder) == "02"


def test_save_measurement_writes_file(tmp_path) -> None:
    data = np.arange(16, dtype=float).reshape(4, 4)
    path = save_measurement(data, base_dir=tmp_path)
    assert path.exists()
    loaded = np.loadtxt(path)
    np.testing.assert_allclose(loaded, data)
