import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from monitoring import configure_logging, log_error_event, record_request
from routers.auth_router import router as auth_router
from routers.student_router import router as student_router
from routers.monitoring_router import router as monitoring_router

configure_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_and_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        log_error_event("Unhandled request error", str(exc))
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        record_request(request.method, request.url.path, status_code, duration_ms)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "Student Management System"}


app.include_router(auth_router)
app.include_router(student_router)
app.include_router(monitoring_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)
