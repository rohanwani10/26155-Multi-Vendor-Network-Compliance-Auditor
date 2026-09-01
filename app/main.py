from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import compliance, devices, reports, training

app = FastAPI(title="Multi-Vendor Network Compliance Auditor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router)
app.include_router(training.router)
app.include_router(compliance.router)
app.include_router(reports.router)






@app.get("/health")
def health():
    return {"status": "ok"}
