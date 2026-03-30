from fastapi import FastAPI, UploadFile, File, Header, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
import aiofiles
from typing import Optional, Dict, List
import shutil

# Inicializace FastAPI aplikace
app = FastAPI(
    title="Object Storage Service",
    description="Mini S3-inspired cloud storage",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfigurace storage
STORAGE_DIR = Path("storage")
METADATA_FILE = Path("metadata.json")
STORAGE_DIR.mkdir(exist_ok=True)

# Inicializace metadata souboru
if not METADATA_FILE.exists():
    with open(METADATA_FILE, "w") as f:
        json.dump({}, f, indent=2)

print(f"✅ Storage directory: {STORAGE_DIR.absolute()}")
print(f"✅ Metadata file: {METADATA_FILE.absolute()}")


def get_metadata() -> Dict:
    """Načte metadata z JSON souboru"""
    try:
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_metadata(metadata: Dict) -> None:
    """Uloží metadata do JSON souboru"""
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def verify_user_access(file_id: str, user_id: str) -> bool:
    """Ověří, že uživatel má přístup k souboru"""
    metadata = get_metadata()
    if file_id not in metadata:
        return False
    return metadata[file_id]["user_id"] == user_id


# ============ ROOT ENDPOINT ============

@app.get("/")
async def root():
    """Root endpoint - vrátí info o API"""
    return {
        "message": "Object Storage Service",
        "version": "1.0.0",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Object Storage",
        "version": "1.0.0"
    }


# ============ FILE OPERATIONS ============

@app.post("/files/upload")
async def upload_file(
        file: UploadFile = File(...),
        x_user_id: str = Header(..., alias="X-User-ID")
):
    """
    Nahraje soubor a vrátí metadata.

    Header: X-User-ID - identifikátor uživatele

    Vrací: {id, filename, size}
    """
    try:
        print(f"📤 Upload: user={x_user_id}, file={file.filename}")

        # Generuj unikátní ID
        file_id = str(uuid.uuid4())

        # Vytvoř adresář pro uživatele
        user_storage = STORAGE_DIR / x_user_id
        user_storage.mkdir(exist_ok=True)

        # Cesta k souboru
        file_path = user_storage / file_id

        # Ulož soubor
        file_content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        print(f"✅ Soubor uložen: {file_path}")

        # Ulož metadata
        metadata = get_metadata()
        metadata[file_id] = {
            "id": file_id,
            "user_id": x_user_id,
            "filename": file.filename,
            "path": str(file_path),
            "size": len(file_content),
            "created_at": datetime.now().isoformat()
        }
        save_metadata(metadata)

        print(f"✅ Metadata uložena: {file_id}")

        return {
            "id": file_id,
            "filename": file.filename,
            "size": len(file_content)
        }

    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload selhal: {str(e)}"
        )


@app.get("/files/{file_id}")
async def download_file(
        file_id: str,
        x_user_id: str = Header(..., alias="X-User-ID")
):
    """
    Stáhne soubor pro uživatele.

    Header: X-User-ID - identifikátor uživatele
    """
    print(f"📥 Download: user={x_user_id}, file_id={file_id}")

    # Ověř přístup
    if not verify_user_access(file_id, x_user_id):
        print(f"❌ Přístup zamítnut")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Soubor nenalezen nebo nemáš přístup"
        )

    # Získej metadata
    metadata = get_metadata()
    file_info = metadata[file_id]
    file_path = Path(file_info["path"])

    # Ověř, že soubor existuje
    if not file_path.exists():
        print(f"❌ Soubor fyzicky neexistuje: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Soubor nenalezen"
        )

    print(f"✅ Soubor stažen: {file_path}")

    return FileResponse(
        path=file_path,
        filename=file_info["filename"]
    )


@app.delete("/files/{file_id}")
async def delete_file(
        file_id: str,
        x_user_id: str = Header(..., alias="X-User-ID")
):
    """
    Smaže soubor a jeho metadata.

    Header: X-User-ID - identifikátor uživatele
    """
    print(f"🗑️  Delete: user={x_user_id}, file_id={file_id}")

    # Ověř přístup
    if not verify_user_access(file_id, x_user_id):
        print(f"❌ Přístup zamítnut")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Soubor nenalezen nebo nemáš přístup"
        )

    # Získej metadata
    metadata = get_metadata()
    file_info = metadata[file_id]
    file_path = Path(file_info["path"])

    # Smaž soubor ze storage
    try:
        if file_path.exists():
            file_path.unlink()
            print(f"✅ Soubor smazán: {file_path}")
    except Exception as e:
        print(f"❌ Delete error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Smazání souboru selhalo: {str(e)}"
        )

    # Odstraň metadata
    del metadata[file_id]
    save_metadata(metadata)
    print(f"✅ Metadata odstraněna: {file_id}")

    return {"message": "Soubor smazán"}


@app.get("/files")
async def list_files(
        x_user_id: str = Header(..., alias="X-User-ID")
):
    """
    Vypíše všechny soubory uživatele.

    Header: X-User-ID - identifikátor uživatele
    """
    print(f"📋 List files: user={x_user_id}")

    metadata = get_metadata()

    # Filtruj soubory jen pro daného uživatele
    user_files = [
        file_info
        for file_id, file_info in metadata.items()
        if file_info["user_id"] == x_user_id
    ]

    print(f"✅ Nalezeno {len(user_files)} souborů")

    return {
        "user_id": x_user_id,
        "count": len(user_files),
        "files": user_files
    }


# ============ ERROR HANDLERS ============

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    print(f"❌ Exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 50)
    print("🚀 Object Storage Service")
    print("=" * 50)
    print("📚 Dokumentace: http://localhost:8000/docs")
    print("🏥 Health check: http://localhost:8000/health")
    print("=" * 50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)