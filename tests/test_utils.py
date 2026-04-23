from utils import extract_json


def test_extract_json_direct():
    data = {"key": "value"}
    assert extract_json('{"key": "value"}') == data


def test_extract_json_markdown():
    data = [{"id": "task1"}]
    text = 'Here is the plan:\n```json\n[{"id": "task1"}]\n```\nHope it helps.'
    assert extract_json(text) == data


def test_extract_json_conversational_array():
    data = [1, 2, 3]
    text = "The tasks are [1, 2, 3]. Good luck!"
    assert extract_json(text) == data


def test_extract_json_nested_delimiters():
    data = {"outer": {"inner": [1, 2]}}
    text = 'Results: {"outer": {"inner": [1, 2]}} end.'
    assert extract_json(text) == data


def test_extract_json_invalid():
    assert extract_json("No JSON here") is None


def test_extract_json_empty():
    assert extract_json("") is None
    assert extract_json(None) is None
