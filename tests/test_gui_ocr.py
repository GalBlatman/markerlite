"""OCR status logic, using no network or Tk widgets."""

import pytest

from markerlite.gui_ocr import ocr_status


@pytest.mark.parametrize("version", ["tesseract 4.1.1", "tesseract v3.05.02"])
def test_older_engine_flag(version):
    status = ocr_status("/ocr/tesseract", version)
    assert status.outdated and "Outdated" in status.message


@pytest.mark.parametrize(
    "version", ["tesseract 5.0.0", "tesseract v5.5.0", "tesseract 6.0.0"]
)
def test_supported_engine(version):
    status = ocr_status("/ocr/tesseract", version)
    assert not status.outdated and "ready" in status.message


def test_missing_or_unknown_version_is_actionable():
    missing = ocr_status(None, None)
    assert missing.path is None and "Preferences" in missing.message
    unknown = ocr_status("/ocr/tesseract", "tesseract (version unknown)")
    assert not unknown.outdated and "could not be read" in unknown.message
