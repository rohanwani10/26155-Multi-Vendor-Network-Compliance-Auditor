import io
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup

from app.models import Device

FIXTURES = Path(__file__).parent / "fixtures" / "configs"


def _upload(client, filename, content, content_type="text/plain"):
    return client.post(
        "/devices/upload",
        files={"file": (filename, content, content_type)},
    )


def test_upload_single_cisco_config_detects_vendor(client, db_session):
    content = (FIXTURES / "cisco_ios_1.cfg").read_bytes()
    response = _upload(client, "cisco_ios_1.cfg", content)
    assert response.status_code == 200

    devices = db_session.query(Device).all()
    assert len(devices) == 1
    assert devices[0].filename == "cisco_ios_1.cfg"
    assert devices[0].vendor == "cisco"


def test_upload_zip_creates_one_device_per_file(client, db_session):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("cisco_ios_1.cfg", (FIXTURES / "cisco_ios_1.cfg").read_text())
        zf.writestr("juniper_1.cfg", (FIXTURES / "juniper_1.cfg").read_text())
        zf.writestr("paloalto_1.cfg", (FIXTURES / "paloalto_1.cfg").read_text())
    buf.seek(0)

    response = _upload(client, "bundle.zip", buf.read(), content_type="application/zip")
    assert response.status_code == 200

    devices = db_session.query(Device).all()
    assert len(devices) == 3
    assert {d.vendor for d in devices} == {"cisco", "juniper", "paloalto"}


def test_upload_unrecognizable_file_defaults_to_unknown_without_crashing(client, db_session):
    content = (FIXTURES / "unknown_device.txt").read_bytes()
    response = _upload(client, "unknown_device.txt", content)
    assert response.status_code == 200

    devices = db_session.query(Device).all()
    assert len(devices) == 1
    assert devices[0].vendor == "unknown"


def test_upload_page_lists_uploaded_device(client, db_session):
    content = (FIXTURES / "cisco_ios_1.cfg").read_bytes()
    _upload(client, "cisco_ios_1.cfg", content)

    response = client.get("/upload")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text()
    assert "cisco_ios_1.cfg" in page_text
    assert "cisco" in page_text
