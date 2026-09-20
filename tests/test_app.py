from streamlit.testing.v1 import AppTest


def test_demo_app_renders_without_vector_index() -> None:
    app = AppTest.from_file("../app.py", default_timeout=15).run()

    assert not app.exception
    assert len(app.selectbox) == 1
    assert len(app.button) == 2
    assert [metric.label for metric in app.metric] == [
        "Nguồn",
        "Trang PDF",
        "Legal records",
    ]
