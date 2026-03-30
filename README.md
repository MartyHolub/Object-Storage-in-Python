# Object Storage in Python

A lightweight, S3-inspired object storage service built with **FastAPI** and **SQLAlchemy**. Files are stored on disk and their metadata is persisted in a SQLite database, providing a simple yet functional cloud-storage-like backend.

## Features

- **Upload files** – store any file via a multipart POST request
- **Download files** – retrieve a previously uploaded file by its ID
- **List files** – view all files belonging to a specific user
- **Delete files** – remove a file and its metadata in a single operation
- **Per-user access control** – every request must carry an `X-User-ID` header; users can only access their own files
- **Async I/O** – file reads and writes use `aiofiles` for non-blocking performance
- **Auto-generated docs** – Swagger UI available at `/docs`

## Tech Stack

| Component        | Library / Tool             |
|------------------|----------------------------|
| Web framework    | FastAPI 0.104              |
| ASGI server      | Uvicorn (with `standard` extras) |
| Async file I/O   | aiofiles 23.2              |
| ORM / database   | SQLAlchemy 2.0 + SQLite    |
| File upload      | python-multipart 0.0.6     |

## Prerequisites

- Python 3.10+
- `pip`

## Installation

```bash
# Clone the repository
git clone https://github.com/MartyHolub/Object-Storage-in-Python.git
cd Object-Storage-in-Python

# (Optional) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Server

```bash
python main.py
```

The server starts on **http://localhost:8000**.

| URL                           | Description              |
|-------------------------------|--------------------------|
| http://localhost:8000/        | Service info             |
| http://localhost:8000/health  | Health check             |
| http://localhost:8000/docs    | Interactive Swagger UI   |

## API Reference

All file endpoints require the `X-User-ID` header to identify the caller.

### Health & Info

| Method | Path      | Description             |
|--------|-----------|-------------------------|
| GET    | `/`       | Returns service info    |
| GET    | `/health` | Returns health status   |

### File Operations

| Method | Path                  | Description                        |
|--------|-----------------------|------------------------------------|
| POST   | `/files/upload`       | Upload a file                      |
| GET    | `/files`              | List all files for the current user|
| GET    | `/files/{file_id}`    | Download a file by ID              |
| DELETE | `/files/{file_id}`    | Delete a file by ID                |

#### Upload a File

```http
POST /files/upload
X-User-ID: <user_id>
Content-Type: multipart/form-data

file=<binary data>
```

**Response**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "example.txt",
  "size": 1024
}
```

#### List Files

```http
GET /files
X-User-ID: <user_id>
```

**Response**

```json
{
  "user_id": "user_123",
  "count": 2,
  "files": [
    {
      "id": "550e8400-...",
      "user_id": "user_123",
      "filename": "example.txt",
      "path": "storage/user_123/550e8400-...",
      "size": 1024,
      "created_at": "2026-03-30T12:00:00"
    }
  ]
}
```

#### Download a File

```http
GET /files/{file_id}
X-User-ID: <user_id>
```

Returns the file as a binary download. Returns `404` if the file does not exist or belongs to a different user.

#### Delete a File

```http
DELETE /files/{file_id}
X-User-ID: <user_id>
```

**Response**

```json
{ "message": "Soubor smazán" }
```

## Testing

A shell script that exercises all endpoints against a running server is included:

```bash
# Make sure the server is running first
python main.py &

bash test_api.sh
```

The script performs the following steps:

1. Health check
2. Root endpoint
3. Upload file 1
4. List files (1 file)
5. Download file 1
6. Upload file 2
7. List files (2 files)
8. Delete file 1
9. List files (1 file)
10. Access file 2 as a different user → expects 404
11. Delete file 2

## Project Structure

```
.
├── main.py          # FastAPI application – all routes and business logic
├── requirements.txt # Python dependencies
├── test_api.sh      # End-to-end API test script
├── metadata.json    # Legacy placeholder (no longer used)
└── storage/         # Created at runtime; files are stored here per user
```

## Changelog

### v1.0.0

#### Replace JSON metadata storage with SQLAlchemy

Previously, file metadata was persisted in a flat `metadata.json` file. This approach did not scale and was not safe for concurrent access. The metadata layer has been replaced with **SQLAlchemy 2.0** backed by a **SQLite** database (`metadata.db`).

Key changes:

- Added `sqlalchemy==2.0.23` to `requirements.txt`.
- Introduced a `FileRecord` ORM model with the following columns:
  - `id` – UUID primary key
  - `user_id` – owner of the file
  - `filename` – original file name
  - `path` – absolute path on disk
  - `size` – file size in bytes
  - `created_at` – upload timestamp
- All CRUD operations (upload, download, list, delete) now use SQLAlchemy `Session`.
- Upload is atomic: if saving metadata fails, the physical file is automatically removed to avoid orphaned data.
- `metadata.json` is no longer written to or read from.

## License

This project is provided as-is for educational purposes.
