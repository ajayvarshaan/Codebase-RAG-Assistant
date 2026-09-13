from types import SimpleNamespace

from services import code_diff_service


class FakeQuery:
    def __init__(self, project):
        self.project = project

    def filter(self, *_args):
        return self

    def first(self):
        return self.project


class FakeDB:
    def __init__(self, project):
        self.project = project

    def query(self, *_args):
        return FakeQuery(self.project)


def test_code_diff_service_builds_ai_request(monkeypatch):
    captured = {}

    def fake_generate_answer(question, context, conversation_history):
        captured["question"] = question
        captured["context"] = context
        captured["history"] = conversation_history
        return "analysis"

    monkeypatch.setattr(
        code_diff_service,
        "generate_answer",
        fake_generate_answer
    )

    db = FakeDB(SimpleNamespace(id=1, name="Demo Project"))

    result = code_diff_service.generate_code_diff_analysis(
        db=db,
        project_id=1,
        file_name="src/app.js",
        old_code="return a + b;",
        new_code="return a - b;"
    )

    assert result == "analysis"
    assert "src/app.js" in captured["question"]
    assert "return a + b;" in captured["context"]
    assert "return a - b;" in captured["context"]
    assert captured["history"] == ""


def test_code_diff_service_handles_missing_project(monkeypatch):
    monkeypatch.setattr(
        code_diff_service,
        "generate_answer",
        lambda *args, **kwargs: "should not run"
    )

    db = FakeDB(None)

    result = code_diff_service.generate_code_diff_analysis(
        db=db,
        project_id=999,
        file_name="missing.js",
        old_code="old",
        new_code="new"
    )

    assert result == "Could not find the selected project."
