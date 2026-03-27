from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Run the REST API with a single worker."""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(
        "rest.app:app",
        host=host,
        port=port,
        workers=1,
    )


if __name__ == "__main__":
    main()
