#!/usr/bin/env python3
"""Fetch JSON from a REST API and save selected records as CSV.

Example:
    python api_to_csv.py \
        --url https://jsonplaceholder.typicode.com/posts \
        --output posts.csv
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Iterable


def fetch_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 3,
) -> Any:
    request_headers = {
        "User-Agent": "api-to-csv-script/1.0",
        "Accept": "application/json",
    }
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(
        url,
        headers=request_headers,
    )

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(1)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Unable to fetch JSON response.")


def flatten_value(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key, item in value.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, (dict, list)):
                flattened.update(flatten_value(item, new_prefix))
            else:
                flattened[new_prefix] = item
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, item in enumerate(value):
            key = f"{prefix}[{index}]" if prefix else f"[{index}]"
            if isinstance(item, (dict, list)):
                flattened.update(flatten_value(item, key))
            else:
                flattened[key] = item
        return flattened
    return {prefix: value} if prefix else {}


def normalize_records(payload: Any, root_key: str | None = None) -> list[dict[str, Any]]:
    if root_key:
        if not isinstance(payload, dict):
            raise ValueError(f"Payload must be an object when --root-key is used, got {type(payload).__name__}")
        payload = payload.get(root_key)

    if isinstance(payload, list):
        return [item if isinstance(item, dict) else {"value": item} for item in payload]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(
        f"Unsupported payload shape: expected a JSON object, object containing a list, or list; got {type(payload).__name__}"
    )


def paginate_records(
    url: str,
    headers: dict[str, str],
    root_key: str | None = None,
    page_param: str = "page",
    page_size: int | None = None,
    max_pages: int = 5,
    timeout: int = 30,
    retries: int = 3,
) -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    page = 1

    while page <= max_pages:
        request_url = url
        if page_param and page_size is not None:
            separator = "&" if "?" in request_url else "?"
            request_url = f"{request_url}{separator}{page_param}={page}&per_page={page_size}"
        elif page_param:
            separator = "&" if "?" in request_url else "?"
            request_url = f"{request_url}{separator}{page_param}={page}"

        payload = fetch_json(
            request_url,
            headers=headers,
            timeout=timeout,
            retries=retries,
        )
        records = normalize_records(payload, root_key)
        if not records:
            break
        all_records.extend(records)

        if not isinstance(payload, dict):
            break

        next_url = payload.get("next") if isinstance(payload, dict) else None
        if isinstance(next_url, str) and next_url:
            request_url = next_url
            payload = fetch_json(
                next_url,
                headers=headers,
                timeout=timeout,
                retries=retries,
            )
            records = normalize_records(payload, root_key)
            if not records:
                break
            all_records.extend(records)
            break

        if page_size is not None and len(records) < page_size:
            break

        page += 1

    return all_records


def select_fields(records: Iterable[dict[str, Any]], fields: list[str] | None) -> list[str]:
    if fields:
        return fields
    all_keys = sorted({key for record in records for key in record.keys()})
    return all_keys


def write_csv(records: list[dict[str, Any]], output_path: str, fields: list[str] | None = None) -> None:
    selected_fields = select_fields(records, fields)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=selected_fields)
        writer.writeheader()
        for record in records:
            row = {}
            for field in selected_fields:
                row[field] = record.get(field, "")
            writer.writerow(row)


def write_summary(
    summary_path: str | None,
    url: str,
    output_path: str,
    row_count: int,
) -> None:
    if not summary_path:
        return

    summary = {
        "url": url,
        "output": output_path,
        "row_count": row_count,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")


def load_config_file(config_path: str) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError("Config file must contain a JSON object.")
    return config


def parse_args() -> argparse.Namespace:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--config",
        default=None,
        help="Optional path to a JSON config file with default arguments.",
    )
    pre_args, _ = pre_parser.parse_known_args()

    config_defaults: dict[str, Any] = {}
    if pre_args.config:
        config_defaults = load_config_file(pre_args.config)
        config_defaults = {
            key.replace("-", "_"): value for key, value in config_defaults.items()
        }

    parser = argparse.ArgumentParser(
        description="Fetch JSON from a REST API and write it to a CSV file."
    )
    parser.add_argument(
        "--config",
        default=config_defaults.get("config"),
        help="Optional path to a JSON config file with default arguments.",
    )
    parser.add_argument(
        "--url",
        default=config_defaults.get("url"),
        help="The API endpoint URL to fetch.",
    )
    parser.add_argument(
        "--output",
        default=config_defaults.get("output", "output.csv"),
        help="Path for the CSV file to be created (default: output.csv).",
    )
    parser.add_argument(
        "--root-key",
        default=config_defaults.get("root_key"),
        help="Optional key to use when the response JSON is an object containing the records list.",
    )
    parser.add_argument(
        "--fields",
        default=config_defaults.get("fields"),
        help="Optional comma-separated list of columns to export.",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=config_defaults.get("header", []),
        help=(
            "Additional request header to send. Use the format 'Header-Name: value'. "
            "May be provided multiple times."
        ),
    )
    parser.add_argument(
        "--username",
        default=config_defaults.get("username"),
        help="Optional username for HTTP Basic Authentication.",
    )
    parser.add_argument(
        "--password",
        default=config_defaults.get("password"),
        help="Optional password for HTTP Basic Authentication.",
    )
    parser.add_argument(
        "--token",
        default=config_defaults.get("token"),
        help="Optional bearer token to send in the Authorization header.",
    )
    parser.add_argument(
        "--page-param",
        default=config_defaults.get("page_param"),
        help="Query parameter used for pagination (for example, 'page').",
    )
    parser.add_argument(
        "--page-size",
        default=config_defaults.get("page_size"),
        type=int,
        help="Optional page size to append when paginating.",
    )
    parser.add_argument(
        "--max-pages",
        default=config_defaults.get("max_pages", 5),
        type=int,
        help="Maximum number of pages to fetch when pagination is enabled.",
    )
    parser.add_argument(
        "--timeout",
        default=config_defaults.get("timeout", 30),
        type=int,
        help="Request timeout in seconds for each API call.",
    )
    parser.add_argument(
        "--retries",
        default=config_defaults.get("retries", 3),
        type=int,
        help="Number of retries for transient request failures.",
    )
    parser.add_argument(
        "--summary-file",
        default=config_defaults.get("summary_file"),
        help="Optional file path to write a small summary JSON containing row counts and URL.",
    )
    args = parser.parse_args()

    if not args.url:
        parser.error("the following arguments are required: --url")

    return args


def parse_headers(header_values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in header_values:
        if ":" not in value:
            raise ValueError(
                f"Invalid header format: {value!r}. Expected 'Header-Name: value'."
            )
        name, header_value = value.split(":", 1)
        headers[name.strip()] = header_value.strip()
    return headers


def main() -> None:
    args = parse_args()

    if isinstance(args.fields, str):
        fields = [field.strip() for field in args.fields.split(",") if field.strip()]
    else:
        fields = args.fields

    try:
        headers = parse_headers(args.header)

        if args.username is None and args.password is None and os.getenv("API_USERNAME"):
            args.username = os.getenv("API_USERNAME")
        if args.password is None and os.getenv("API_PASSWORD"):
            args.password = os.getenv("API_PASSWORD")
        if args.token is None and os.getenv("API_TOKEN"):
            args.token = os.getenv("API_TOKEN")

        if args.username is not None or args.password is not None:
            if args.username is None or args.password is None:
                raise ValueError(
                    "Both --username and --password must be provided together for basic auth."
                )
            credentials = base64.b64encode(
                f"{args.username}:{args.password}".encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = f"Basic {credentials}"
        elif args.token:
            headers["Authorization"] = f"Bearer {args.token}"

        if args.page_param:
            records = paginate_records(
                args.url,
                headers=headers,
                root_key=args.root_key,
                page_param=args.page_param,
                page_size=args.page_size,
                max_pages=args.max_pages,
                timeout=args.timeout,
                retries=args.retries,
            )
        else:
            payload = fetch_json(
                args.url,
                headers=headers,
                timeout=args.timeout,
                retries=args.retries,
            )
            records = normalize_records(payload, args.root_key)

        write_csv(records, args.output, fields)
        write_summary(
            args.summary_file,
            args.url,
            args.output,
            len(records),
        )
    except ValueError as exc:
        raise SystemExit(str(exc))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP error {exc.code} while fetching {args.url}: {exc.reason}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"URL error while fetching {args.url}: {exc.reason}")
    except (json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Failed to process response: {exc}")

    print(f"Wrote {len(records)} row(s) to {args.output}")


if __name__ == "__main__":
    main()
