from utils import extract_json


def test_extract_json():
    # Test with string
    assert extract_json('{"a": 1}') == {"a": 1}

    # Test with list
    data_list = [{"id": "task1"}]
    assert extract_json(data_list) == data_list

    # Test with dict
    data_dict = {"tasks": []}
    assert extract_json(data_dict) == data_dict

    # Test with None
    assert extract_json(None) is None

    print("Extract JSON tests passed!")


if __name__ == "__main__":
    test_extract_json()
