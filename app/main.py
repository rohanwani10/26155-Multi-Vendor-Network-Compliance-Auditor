from fastapi import FastAPI

from app.routers import compliance, devices, training

app = FastAPI(title="Multi-Vendor Network Compliance Auditor")
app.include_router(devices.router)
app.include_router(training.router)
app.include_router(compliance.router)




@app.get("/health")
def health():
    return {"status": "ok"}
