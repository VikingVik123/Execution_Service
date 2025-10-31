from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import signal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signal.router)
@app.get("/")
async def root():
    return {"message": "Execution Service is running."}


