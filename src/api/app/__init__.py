from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.ecommerce import router as ecommerce_router
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
    app.include_router(ecommerce_router)

    return app
