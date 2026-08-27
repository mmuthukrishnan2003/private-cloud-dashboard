from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings

from .routers import host
from .routers import network
from .routers import storage
from .routers import vms


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


# ============================================================
# CORS
# ============================================================
#
# Angular development server:
#     http://localhost:4200
#
# Dashboard server:
#     http://172.16.0.111:2625
#
# CORS allows the Angular frontend to communicate
# with the FastAPI backend.
#
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://172.16.0.111:2625",
        "http://localhost:4200",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# API ROUTERS
# ============================================================
#
# Host
#   Server CPU, RAM, disk, system information, etc.
#
# Network
#   Network interfaces, IP information, traffic, etc.
#
# Storage
#   Storage pools, ISO files, disk images, uploads, etc.
#
# VMs
#   KVM virtual machine management.
#
# ============================================================

app.include_router(host.router)

app.include_router(network.router)

app.include_router(storage.router)

app.include_router(vms.router)


# ============================================================
# ROOT API
# ============================================================

@app.get("/")
def root():
    """
    Basic API information and server status.
    """

    return {
        "application": settings.APP_NAME,
        "server": settings.HOST_NAME,
        "server_ip": settings.HOST_IP,
        "status": "online",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    """
    Simple API health check.

    Used by:
        - Dashboard
        - Nginx
        - Monitoring
        - Load balancer
    """

    return {
        "status": "healthy",
        "host": settings.HOST_NAME,
        "ip": settings.HOST_IP,
    }
