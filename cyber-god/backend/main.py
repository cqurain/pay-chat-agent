from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import ALLOWED_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MCP session wired in tools/price.py — see Plan 02
    yield


app = FastAPI(title="Cyber God of Wealth API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
