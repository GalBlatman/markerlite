import pytest

from markerlite.extraction import discover_tesseract, tesseract_version


def fake_which(paths):
    def find(command, path=None):
        assert path == "SEARCH"
        return paths.get(command)

    return find


def test_configured_command_has_priority(tmp_path):
    configured = tmp_path / "configured" / "tesseract.exe"
    path_copy = tmp_path / "path" / "tesseract.exe"
    files = {configured, path_copy}
    assert discover_tesseract(
        env={"TESSERACT_CMD": str(configured), "PATH": "SEARCH"},
        which=fake_which({"tesseract": str(path_copy)}),
        is_file=files.__contains__,
        registry_reader=lambda: [],
    ) == str(configured.resolve())


def test_path_precedes_registry_and_default_directories(tmp_path):
    path_copy = tmp_path / "path" / "tesseract.exe"
    assert discover_tesseract(
        env={"PATH": "SEARCH", "ProgramFiles": str(tmp_path / "programs")},
        which=fake_which({"tesseract": str(path_copy)}),
        is_file=lambda _path: False,
        registry_reader=lambda: [str(tmp_path / "registry")],
    ) == str(path_copy.resolve())


def test_registry_precedes_default_directories(tmp_path):
    registry = tmp_path / "registry" / "tesseract.exe"
    default = tmp_path / "programs" / "Tesseract-OCR" / "tesseract.exe"
    assert discover_tesseract(
        env={"PATH": "SEARCH", "ProgramFiles": str(tmp_path / "programs")},
        which=fake_which({}),
        is_file={registry, default}.__contains__,
        registry_reader=lambda: [str(registry.parent)],
    ) == str(registry.resolve())


@pytest.mark.parametrize(
    ("variable", "tail"),
    [
        ("ProgramFiles", ("Tesseract-OCR", "tesseract.exe")),
        ("ProgramFiles(x86)", ("Tesseract-OCR", "tesseract.exe")),
        ("LOCALAPPDATA", ("Programs", "Tesseract-OCR", "tesseract.exe")),
    ],
)
def test_default_install_directories(tmp_path, variable, tail):
    executable = tmp_path.joinpath(*tail)
    assert discover_tesseract(
        env={"PATH": "SEARCH", variable: str(tmp_path)},
        which=fake_which({}),
        is_file={executable}.__contains__,
        registry_reader=lambda: [],
    ) == str(executable.resolve())


def test_missing_tesseract_returns_none():
    assert (
        discover_tesseract(
            env={"PATH": "SEARCH"},
            which=fake_which({}),
            is_file=lambda _path: False,
            registry_reader=lambda: [],
        )
        is None
    )


def test_version_reports_first_line_and_unknown_on_failure():
    class Result:
        stdout = "tesseract 5.5.0\n leptonica"
        stderr = ""

    assert tesseract_version(
        "/opt/tesseract", run=lambda *_args, **_kwargs: Result()
    ) == ("tesseract 5.5.0")

    def fail(*_args, **_kwargs):
        raise OSError

    assert tesseract_version("/missing", run=fail) == "tesseract (version unknown)"
