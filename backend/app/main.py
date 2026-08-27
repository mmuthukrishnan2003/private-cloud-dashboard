from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import host
from .routers import storage
from .routers import vms


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
# During development Angular may run on port 4200.
# Nginx production deployment can use the same origin.
#
# Note: browsers do not apply CORS to WebSocket upgrade
# requests, so the /api/vms/{name}/console websocket route
# is unaffected by this middleware.
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://172.16.0.111:8080",
        "http://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API Routers
# ---------------------------------------------------------

app.include_router(host.router)
app.include_router(vms.router)
app.include_router(storage.router)


@app.get("/")
def root():
    """
    API health endpoint.
    """

    return {
        "application": settings.APP_NAME,
        "server": settings.HOST_NAME,
        "server_ip": settings.HOST_IP,
        "status": "online",
    }


@app.get("/api/health")
def health():
    """
    Simple health check.
    """

    return {
        "status": "healthy",
        "host": settings.HOST_NAME,
        "ip": settings.HOST_IP,
    }
