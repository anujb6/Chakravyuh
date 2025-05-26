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
    allow_origin_regex=r"(localhost(:\d+)?|127\.0\.0\.1(:\d+)?|0\.0\.0\.0(:\d+)?|::1(:\d+)?)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=["*"],
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

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000, log_level="info")