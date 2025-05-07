"""
Main entry point for running the MCPOSimpleServer as a module.

This allows running the server with `python -m mcpo_simple_server`
"""
import sys
import argparse
import uvicorn
from loguru import logger
from mcpo_simple_server.main import fastapi


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCPOSimpleServer - MCP implementation")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    return parser.parse_args()


def main():
    """Run the server."""
    try:
        args = parse_args()
        logger.info(f"Starting MCPOSimpleServer on {args.host}:{args.port}")
        uvicorn.run(
            "mcpo_simple_server.main:fastapi",
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
