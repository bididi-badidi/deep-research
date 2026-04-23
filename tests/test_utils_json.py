import unittest
from utils import extract_json


class TestExtractJson(unittest.TestCase):
    def test_direct_parsing(self):
        text = '{"key": "value"}'
        self.assertEqual(extract_json(text), {"key": "value"})

    def test_markdown_code_block(self):
        text = 'Here is the JSON:\n```json\n{"key": "value"}\n```\nHope it helps!'
        self.assertEqual(extract_json(text), {"key": "value"})

    def test_markdown_code_block_no_lang(self):
        text = '```\n{"key": "value"}\n```'
        self.assertEqual(extract_json(text), {"key": "value"})

    def test_outermost_delimiters_object(self):
        text = 'Some preamble { "key": "value" } Some postamble'
        self.assertEqual(extract_json(text), {"key": "value"})

    def test_outermost_delimiters_array(self):
        text = "List of items: [1, 2, 3] end."
        self.assertEqual(extract_json(text), [1, 2, 3])

    def test_nested_delimiters(self):
        text = 'Pre { "a": { "b": 1 } } Post'
        self.assertEqual(extract_json(text), {"a": {"b": 1}})

    def test_invalid_json(self):
        text = "This is not JSON { incomplete: "
        self.assertIsNone(extract_json(text))

    def test_empty_input(self):
        self.assertIsNone(extract_json(""))
        self.assertIsNone(extract_json(None))

    def test_malformed_but_delimited(self):
        text = "Prefix { this is not json } suffix"
        self.assertIsNone(extract_json(text))


if __name__ == "__main__":
    unittest.main()
