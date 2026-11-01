import shutil
from importlib.resources import files

import pytest

from mobiraeon.persistence import Store


@pytest.fixture
def store(tmp_path):
    store = Store(tmp_path / "store.sqlite3", timeout=0.1)
    store.initialize()
    yield store
    store.close()


@pytest.fixture
def migrations(tmp_path):
    path = tmp_path / "migrations"
    shutil.copytree(files("mobiraeon.persistence").joinpath("migrations"), path)
    return path


def revision(path, number, previous, body):
    (path / "versions" / f"{number}_fixture.py").write_text(
        "from alembic import op\nimport sqlalchemy as sa\n"
        f"revision = {number!r}\ndown_revision = {previous!r}\n"
        "branch_labels = None\ndepends_on = None\n"
        f"def upgrade():\n{body}\n",
        encoding="utf-8",
    )
