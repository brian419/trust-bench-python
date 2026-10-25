from pytest import raises

from report_browser import list_saved_reports


def test_list_saved_reports(tmp_path):
    first = tmp_path / "evaluation-first.json"
    second = tmp_path / "evaluation-second.json"

    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")

    reports = list_saved_reports(str(tmp_path))

    assert set(reports) == {
        str(first),
        str(second),
    }


def test_list_saved_reports_ignores_other_files(tmp_path):
    valid = tmp_path / "evaluation-123.json"
    unrelated = tmp_path / "other.json"
    text_file = tmp_path / "evaluation-123.txt"

    valid.write_text("{}", encoding="utf-8")
    unrelated.write_text("{}", encoding="utf-8")
    text_file.write_text("text", encoding="utf-8")

    reports = list_saved_reports(str(tmp_path))

    assert reports == [str(valid)]


def test_list_saved_reports_missing_directory(tmp_path):
    missing = tmp_path / "missing"

    assert list_saved_reports(str(missing)) == []


def test_list_saved_reports_rejects_file_path(tmp_path):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("data", encoding="utf-8")

    with raises(ValueError, match="not a directory"):
        list_saved_reports(str(file_path))
