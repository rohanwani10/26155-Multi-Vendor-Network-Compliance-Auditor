from fastapi import FastAPI

from app.routers import devices

app = FastAPI(title="Multi-Vendor Network Compliance Auditor")
app.include_router(devices.router)


@app.get("/health")
def health():
    return {"status": "ok"}
