from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.hrpolicy import router as hrpolicy_router
from .routes.feedback import router as feedback_router
from .logger import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    app = FastAPI()

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(hrpolicy_router)
    app.include_router(feedback_router)

    return app
