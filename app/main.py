from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa
from app.database import Base, engine
from app.routers import compliance, devices, health_advisor, reports, training

Base.metadata.create_all(bind=engine)

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
app.include_router(health_advisor.router)


@app.get("/health")
def health():
    return {"status": "ok"}
