from fastapi import FastAPI

from app.routers import auth, categories, dashboard, transactions, uploads

app = FastAPI(title="Finance Leak Detector")

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(uploads.router)
app.include_router(dashboard.router)
app.include_router(categories.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}