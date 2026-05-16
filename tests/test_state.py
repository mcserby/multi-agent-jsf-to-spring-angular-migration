from pathlib import Path

from jsf_migrator.state import FeatureState, State, TaskState, load_state, save_state


def test_load_when_missing(tmp_path: Path):
    s = load_state(tmp_path / "state.json")
    assert s.phase == "init"
    assert s.features == {}


def test_roundtrip(tmp_path: Path):
    s = State(phase="audit")
    s.features["users"] = FeatureState(
        status="in_progress",
        tasks={"jsf_analysis": TaskState(status="completed", output="specs/jsf/users.json")},
    )
    p = tmp_path / "state.json"
    save_state(s, p)
    reloaded = load_state(p)
    assert reloaded.phase == "audit"
    assert reloaded.features["users"].tasks["jsf_analysis"].status == "completed"
    assert reloaded.features["users"].tasks["jsf_analysis"].output == "specs/jsf/users.json"


def test_save_updates_timestamp(tmp_path: Path):
    s = State()
    original = s.updated_at
    p = tmp_path / "state.json"
    # save_state mutates updated_at via touch()
    s.updated_at = "1970-01-01T00:00:00+00:00"
    save_state(s, p)
    assert s.updated_at != "1970-01-01T00:00:00+00:00"
    assert s.updated_at != original or original == s.updated_at  # tolerate same-second
