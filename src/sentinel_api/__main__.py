import uvicorn

from .config import get_settings


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "sentinel_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment.lower() == "development",
    )


if __name__ == "__main__":
    run()
