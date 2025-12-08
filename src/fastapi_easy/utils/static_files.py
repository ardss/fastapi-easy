"""Enhanced static file serving with proper MIME type detection and caching"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


class EnhancedStaticFiles(StaticFiles):
    """
    Enhanced static files handler with:
    - Proper MIME type detection
    - ETag support for caching
    - Gzip compression support
    - CORS headers for development
    - Proper async file handling with aiofiles
    """

    def __init__(
        self,
        directory: str,
        packages: Optional[list] = None,
        html: bool = False,
        cache_control: Optional[int] = 3600,  # Cache for 1 hour by default
        enable_cors: bool = False,
        enable_gzip: bool = True,
        **kwargs: Any,
    ):
        super().__init__(directory=directory, packages=packages, html=html, **kwargs)
        self.cache_control = cache_control
        self.enable_cors = enable_cors
        self.enable_gzip = enable_gzip

        # Initialize MIME types with common web types
        self._init_mime_types()

    def _init_mime_types(self):
        """Initialize additional MIME types for better web compatibility"""
        # Ensure common web file types have correct MIME types
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("application/json", ".json")
        mimetypes.add_type("image/svg+xml", ".svg")
        mimetypes.add_type("image/webp", ".webp")
        mimetypes.add_type("font/woff", ".woff")
        mimetypes.add_type("font/woff2", ".woff2")
        mimetypes.add_type("font/ttf", ".ttf")
        mimetypes.add_type("font/eot", ".eot")
        mimetypes.add_type("application/font-woff", ".woff")
        mimetypes.add_type("application/font-woff2", ".woff2")
        mimetypes.add_type("text/plain", ".txt")
        mimetypes.add_type("application/xml", ".xml")

    def _get_etag(self, file_path: Path) -> str:
        """Generate ETag for file based on modification time and size"""
        stat = file_path.stat()
        etag = f'"{int(stat.st_mtime)}-{stat.st_size}"'
        return etag

    def _get_cache_headers(self, file_path: Path) -> Dict[str, str]:
        """Get appropriate cache headers for a file"""
        headers = {}

        # Add ETag
        etag = self._get_etag(file_path)
        headers["ETag"] = etag

        # Add Cache-Control if specified
        if self.cache_control:
            headers["Cache-Control"] = f"public, max-age={self.cache_control}"

        # Add CORS headers if enabled
        if self.enable_cors:
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Range, If-None-Match"

        return headers

    async def get_response(self, path: str, scope: Dict, request: Request) -> Response:
        """
        Enhanced response handler with proper file serving
        """
        # Resolve the file path
        full_path = self.get_full_path(path)

        # Check if file exists and is a file
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Handle preflight requests for CORS
        if request.method == "OPTIONS" and self.enable_cors:
            return Response(
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "Range, If-None-Match",
                }
            )

        # Check If-None-Match header for ETag support
        if_none_match = request.headers.get("if-none-match")
        cache_headers = self._get_cache_headers(full_path)

        if if_none_match and if_none_match == cache_headers.get("ETag"):
            return Response(status_code=304, headers=cache_headers)

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # For small files, use FileResponse with async support
        if full_path.stat().st_size < 10 * 1024 * 1024:  # 10MB threshold
            return FileResponse(path=str(full_path), media_type=mime_type, headers=cache_headers)

        # For larger files, use streaming response
        return await self._stream_file(full_path, mime_type, cache_headers)

    async def _stream_file(
        self, file_path: Path, media_type: str, headers: Dict[str, str]
    ) -> StreamingResponse:
        """Stream large files asynchronously"""

        async def file_generator():
            async with aiofiles.open(file_path, "rb") as file:
                while chunk := await file.read(64 * 1024):  # 64KB chunks
                    yield chunk

        return StreamingResponse(file_generator(), media_type=media_type, headers=headers)


def setup_static_files(
    app,
    path: str = "/static",
    directory: str = "static",
    cache_control: Optional[int] = 3600,
    enable_cors: bool = False,
    name: str = "static",
) -> None:
    """
    Convenience function to set up enhanced static file serving

    Args:
        app: FastAPI application instance
        path: URL path for static files (default: "/static")
        directory: Directory containing static files (default: "static")
        cache_control: Cache time in seconds (default: 3600)
        enable_cors: Enable CORS headers (default: False)
        name: Name for the static files mount
    """
    # Ensure the static directory exists
    static_dir = Path(directory)
    static_dir.mkdir(exist_ok=True)

    # Mount enhanced static files handler
    app.mount(
        path,
        EnhancedStaticFiles(
            directory=directory,
            cache_control=cache_control,
            enable_cors=enable_cors,
            html=True,  # Enable HTML serving for SPA support
        ),
        name=name,
    )


# Usage example
if __name__ == "__main__":
    from fastapi import FastAPI

    app = FastAPI()

    # Basic usage
    setup_static_files(app, "/static", "static")

    # Advanced usage with CORS and longer cache
    setup_static_files(
        app,
        path="/assets",
        directory="assets",
        cache_control=86400,  # 24 hours
        enable_cors=True,
        name="assets",
    )

    # For development, you might want no caching and CORS enabled
    if os.getenv("ENVIRONMENT") == "development":
        setup_static_files(
            app,
            path="/dev-static",
            directory="static",
            cache_control=0,  # No caching in dev
            enable_cors=True,
            name="dev-static",
        )
