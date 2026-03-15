from mcp_assistant.utils import _slugify, _parse_index_table


def test_slugify_basic():
    assert _slugify("hello world") == "hello-world"


def test_slugify_accents():
    assert _slugify("Internacionalização Completa") == "internacionalizacao-completa"


def test_slugify_camelcase():
    assert _slugify("MyFeatureName") == "myfeaturename"


def test_slugify_numbers():
    assert _slugify("Feature 123 v2") == "feature-123-v2"


def test_slugify_special_chars():
    assert _slugify("feature/sub-feature!") == "feature-sub-feature"


def test_slugify_multiple_spaces():
    assert _slugify("  hello   world  ") == "hello-world"


def test_parse_index_table_basic():
    text = """\
| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |
| :--- | :--- | :--- | :--- | :--- |
| prd-foo.md | spec-foo.md | Foo Feature | 🟢 Done | ✅ Concluído |
| prd-bar.md | spec-bar.md | Bar Feature | 🟡 Pending | ❌ Todo |
"""
    rows = _parse_index_table(text)
    assert len(rows) == 2
    assert rows[0]["prd"] == "prd-foo.md"
    assert rows[0]["feature"] == "Foo Feature"
    assert rows[1]["implementation"] == "❌ Todo"


def test_parse_index_table_empty():
    assert _parse_index_table("") == []


def test_parse_index_table_header_only():
    text = "| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |\n| :--- | :--- | :--- | :--- | :--- |\n"
    assert _parse_index_table(text) == []
