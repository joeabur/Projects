# API to CSV Script

This project includes a small Python script that fetches JSON from a REST API and writes the results to a CSV file.

## Usage

Run the script with a URL and output file:

```bash
python3 api_to_csv.py \
  --url https://api.example.com/data \
  --output results.csv
```

## Optional arguments

- `--root-key`: If the response JSON is an object containing a records list, specify the key.
- `--fields`: Comma-separated list of columns to export.
- `--header`: Add a custom request header. Can be used multiple times.
- `--username` / `--password`: HTTP Basic Auth credentials.
- `--token`: Bearer token for `Authorization: Bearer ...`.
- `--page-param`: Pagination query parameter name.
- `--page-size`: Page size to append when paginating.
- `--max-pages`: Maximum number of pages to fetch.
- `--timeout`: Request timeout in seconds.
- `--retries`: Number of retries for transient failures.
- `--summary-file`: Optional JSON file that records the URL, output path, and row count.
- `--config`: Optional JSON file that provides default values for the above arguments.

## Config file example

You can load settings from a JSON file like this:

```json
{
  "url": "https://jsonplaceholder.typicode.com/posts",
  "output": "posts.csv",
  "timeout": 15,
  "retries": 2,
  "summary_file": "posts_summary.json"
}
```

Run it with:

```bash
python3 api_to_csv.py --config example_config.json
```

## Environment variables

You can also provide auth values through environment variables:

- `API_USERNAME`
- `API_PASSWORD`
- `API_TOKEN`

Example:

```bash
export API_TOKEN="your-token"
python3 api_to_csv.py \
  --url https://api.example.com/data \
  --output results.csv
```
