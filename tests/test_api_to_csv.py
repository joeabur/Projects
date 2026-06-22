import io
import json
import tempfile
import unittest
from unittest.mock import patch

from api_to_csv import (
    fetch_json,
    flatten_value,
    normalize_records,
    parse_headers,
    select_fields,
    write_csv,
    write_summary,
)


class DummyResponse(io.StringIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


class ApiToCsvTests(unittest.TestCase):
    def test_flatten_value_nested(self):
        data = {
            "id": 1,
            "user": {"name": "Alice", "roles": ["admin", "user"]},
        }
        flattened = flatten_value(data)
        self.assertEqual(flattened["id"], 1)
        self.assertEqual(flattened["user.name"], "Alice")
        self.assertEqual(flattened["user.roles[0]"], "admin")
        self.assertEqual(flattened["user.roles[1]"], "user")

    def test_normalize_records_list(self):
        payload = [{"id": 1}, {"id": 2}]
        records = normalize_records(payload)
        self.assertEqual(records, payload)

    def test_normalize_records_object(self):
        payload = {"id": 1}
        records = normalize_records(payload)
        self.assertEqual(records, [payload])

    def test_normalize_records_root_key(self):
        payload = {"items": [{"id": 5}]}
        records = normalize_records(payload, root_key="items")
        self.assertEqual(records, [{"id": 5}])

    def test_parse_headers_valid(self):
        headers = parse_headers(["X-Test: value", "Accept: application/json"])
        self.assertEqual(headers["X-Test"], "value")
        self.assertEqual(headers["Accept"], "application/json")

    def test_parse_headers_invalid_format(self):
        with self.assertRaises(ValueError):
            parse_headers(["BadHeaderValue"])

    def test_select_fields_default(self):
        records = [{"a": 1, "b": 2}, {"b": 3, "c": 4}]
        fields = select_fields(records, None)
        self.assertEqual(fields, ["a", "b", "c"])

    def test_write_csv_and_summary(self):
        records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        with tempfile.NamedTemporaryFile(mode="r+", suffix=".csv", delete=False) as csv_file:
            write_csv(records, csv_file.name, fields=["id", "name"])
            csv_file.seek(0)
            content = csv_file.read()

        self.assertIn("id,name", content)
        self.assertIn("1,Alice", content)
        self.assertIn("2,Bob", content)

        with tempfile.NamedTemporaryFile(mode="r+", suffix=".json", delete=False) as summary_file:
            write_summary(summary_file.name, "https://example.com", csv_file.name, len(records))
            summary_file.seek(0)
            summary = json.load(summary_file)

        self.assertEqual(summary["url"], "https://example.com")
        self.assertEqual(summary["row_count"], 2)

    @patch("urllib.request.urlopen")
    def test_fetch_json_success(self, mock_urlopen):
        expected_payload = {"name": "test", "value": 42}
        mock_urlopen.return_value = DummyResponse(json.dumps(expected_payload))

        payload = fetch_json("https://api.example.com/data")
        self.assertEqual(payload, expected_payload)


if __name__ == "__main__":
    unittest.main()
