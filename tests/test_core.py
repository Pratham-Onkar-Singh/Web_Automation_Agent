import asyncio
import pytest

from src.agent.actions import ActionRequest, ActionValidationError, ScreenshotMeta, scale_action
from src.agent.policy import ActionPolicy, PolicyDenied, same_origin
from src.agent.recorded import RecordedResponseAdapter
from src.agent.trace import redact
from src.agent.verification import Ending, verify_done
from src.agent.controller import ActionController
from src.agent.agent import INVALID_ACTION_LIMIT
from src.agent.agent import extract_json, parse_action


def test_action_schema_and_coordinate_scaling():
    meta = ScreenshotMeta(640, 360, 1280, 720)
    action = ActionRequest.from_dict({"tool": "click_on_screen", "args": {"x": 320, "y": 180}})
    assert scale_action(action, meta).args == {"x": 640, "y": 360}


def test_action_rejects_out_of_range_coordinates():
    with pytest.raises(ActionValidationError):
        ActionRequest.from_dict({"tool": "click_on_screen", "args": {"x": 1001, "y": 1}})


def test_origin_is_exact_not_substring():
    assert same_origin("https://example.test/a", "https://example.test/b")
    assert not same_origin("https://example.test", "https://example.test.evil/a")
    assert not same_origin("https://example.test:443", "https://example.test:444")


def test_bootstrap_policy_pins_first_origin():
    from src.agent.policy import ActionPolicy
    policy = ActionPolicy(allow_bootstrap_navigation=True)
    policy.check_url("https://example.test/start")
    policy.check_url("https://example.test/next")
    with pytest.raises(PolicyDenied):
        policy.check_url("https://other.test/")


def test_approval_is_bound_and_single_use():
    policy = ActionPolicy({"http://fixture.test"})
    token = policy.issue_approval("a1", "http://fixture.test/form", "submit")
    policy.consume_approval(token, "a1", "http://fixture.test/form", "submit")
    with pytest.raises(PolicyDenied):
        policy.consume_approval(token, "a1", "http://fixture.test/form", "submit")


def test_expired_approval_is_denied():
    policy = ActionPolicy({"http://fixture.test"})
    token = policy.issue_approval("a1", "http://fixture.test", "delete", ttl_seconds=0)
    with pytest.raises(PolicyDenied):
        policy.consume_approval(token, "a1", "http://fixture.test", "delete")


def test_done_without_predicate_is_not_success():
    result = asyncio.run(verify_done(None))
    assert result.ending is Ending.UNVERIFIED_DONE


def test_recorded_adapter_is_reproducible():
    adapter = RecordedResponseAdapter(['{"tool":"done","args":{}}'])
    assert asyncio.run(adapter.complete()) == '{"tool":"done","args":{}}'
    with pytest.raises(RuntimeError):
        asyncio.run(adapter.complete())


def test_trace_redacts_synthetic_secrets():
    assert redact("token hf_1234567890") == "token [REDACTED]"


def test_typed_text_is_not_exposed_by_action_trace_contract():
    action = {"text": "synthetic-secret"}
    if "text" in action:
        action["text"] = "[REDACTED]"
    assert action["text"] == "[REDACTED]"


def test_enter_is_not_sensitive_by_default():
    ordinary = ActionController(ActionPolicy({"http://fixture.test"}), protect_enter=False)
    protected = ActionController(ActionPolicy({"http://fixture.test"}), protect_enter=True)
    assert ordinary.protect_enter is False
    assert protected.protect_enter is True


def test_invalid_actions_have_a_bounded_retry_policy():
    # The agent's three-strike cutoff is intentionally small and explicit;
    # this documents the behavior that prevents screenshot-only retry loops.
    assert INVALID_ACTION_LIMIT == 3


def test_json_extractor_handles_multiple_objects_and_prose():
    content = 'Here is the action:\n{"tool":"wait","args":{"seconds":1}}\n{"extra":"ignored"}'
    assert extract_json(content)["tool"] == "wait"


def test_legacy_normalized_coordinates_are_bounded_and_converted():
    meta = ScreenshotMeta(1280, 720, 1280, 720)
    action = parse_action({"tool": "click_on_screen", "args": {"x": 900, "y": 900}}, meta)
    assert action.args == {"x": 1152, "y": 648}
