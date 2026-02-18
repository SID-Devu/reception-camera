from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import enrollment_routes, recognition_routes, person_routes, analytics_routes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enrollment_routes.router, prefix="/enrollment", tags=["enrollment"])
app.include_router(recognition_routes.router, prefix="/recognition", tags=["recognition"])
app.include_router(person_routes.router, prefix="/person", tags=["person"])
app.include_router(analytics_routes.router, prefix="/analytics", tags=["analytics"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Reception Camera API"}