from fastapi import FastAPI
from backend.routers import employee

app = FastAPI()

app.include_router(employee.router, prefix="/employees", tags=["employees"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
