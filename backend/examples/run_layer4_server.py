"""Launch script for Layer 4: Interactive Blueprint Viewer & Grounded Dialogue Server."""

from pathlib import Path
import uvicorn
from graphite.api.app import create_app


def main():
    print("=" * 75)
    print("GRAPHITE: LAYER 4 INTERACTIVE BLUEPRINT VIEWER & GRAPHRAG API SERVER")
    print("=" * 75)

    app = create_app()

    print("\nStarting Graphite Web Application Server...")
    print("  * Web Viewer: http://127.0.0.1:8000")
    print("  * OpenAPI Docs: http://127.0.0.1:8000/docs")
    print("  * REST API Base: http://127.0.0.1:8000/api")
    print("\nPress Ctrl+C to terminate the server.\n")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
