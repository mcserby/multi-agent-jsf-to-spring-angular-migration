from pathlib import Path

from jsf_migrator.prompts import PromptLoader


def test_bundled_jsf_analyst_loads():
    loader = PromptLoader()
    text = loader.load("jsf_analyst")
    assert "JSF Analyst" in text
    assert "$output_path" in text


def test_template_placeholders_substituted():
    loader = PromptLoader()
    out = loader.render(
        "jsf_analyst",
        {
            "feature_id": "users",
            "feature_description": "User CRUD",
            "jsf_root": "/tmp/jsf",
            "framework_version": "JSF 2.3",
            "bean_style": "CDI",
            "files_block": "jsf:\n  pages:\n    - foo.xhtml\n",
            "output_path": "/tmp/specs/jsf/users.json",
        },
    )
    assert "users" in out
    assert "/tmp/specs/jsf/users.json" in out
    assert "$output_path" not in out


def test_project_override_takes_precedence(tmp_path: Path):
    override_dir = tmp_path / "prompts"
    override_dir.mkdir()
    (override_dir / "jsf_analyst.md").write_text("CUSTOM TEMPLATE for $feature_id", encoding="utf-8")
    loader = PromptLoader(project_prompt_dir=override_dir)
    rendered = loader.render("jsf_analyst", {"feature_id": "x"})
    assert rendered == "CUSTOM TEMPLATE for x"
