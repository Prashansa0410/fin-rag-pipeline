from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import review, research, analytics
from backend.database.session import Base, engine

# For this demo, initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FinResearch AI Backend")

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(review.router)
app.include_router(research.router)
app.include_router(analytics.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
