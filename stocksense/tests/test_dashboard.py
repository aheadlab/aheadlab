from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_three_pages():
    app = AppTest.from_file(str(Path(__file__).parents[1]/'app/streamlit_app.py')).run(timeout=30)
    assert not app.exception
    app.sidebar.radio[0].set_value('Prodotto').run(timeout=30)
    assert not app.exception
    app.sidebar.radio[0].set_value('Risultati').run(timeout=30)
    assert not app.exception
