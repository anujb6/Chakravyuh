import logging.config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import logging
import uvicorn
from routers import router

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger("chkravyuh")
logger.setLevel(logging.DEBUG)

app = FastAPI(
    title="Chakravyuh",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    contact={
        "name": "Chkravyuh"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/mit/"
    }
)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "Sec-WebSocket-Extensions",
        "Sec-WebSocket-Key",
        "Sec-WebSocket-Protocol",
        "Sec-WebSocket-Version",
        "Connection",
        "Upgrade"
    ],
    expose_headers=["*"]
)

@app.get("/health-server", include_in_schema=False)
async def health_check():
    """
    Health check endpoint to verify if the API is running.
    """
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """
    Redirect root URL to the API documentation.
    """
    return RedirectResponse(url="/api/docs")

@app.middleware("http")
async def websocket_cors_middleware(request, call_next):
    if request.url.path.startswith("/api/data/ws/") or request.url.path.startswith("/commodities/ws/"):
        response = await call_next(request)
        return response
    response = await call_next(request)
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")