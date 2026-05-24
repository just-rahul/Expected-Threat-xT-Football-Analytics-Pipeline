"""
Hybrid Sentinel — FastAPI Backend
Stateless REST API serving the merged forensics engine.
Serves the React frontend static build in production.
"""

import io
import json
import os

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm

from engine import ForensicsEngine
from auth import USERS_DB, verify_password, create_access_token, get_current_user, get_analyst_or_admin, ACCESS_TOKEN_EXPIRE_MINUTES, timedelta
from fastapi.staticfiles import StaticFiles


app = FastAPI(
    title="Hybrid Sentinel API",
    description="Money Muling Detection Engine — RIFT 2026",
    version="5.0.0",
)

# ---- CORS (allow all origins for universal deployment) ---- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "engine": "Hybrid Sentinel v5"}


@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "role": current_user["role"]}


def run_engine_safe(df: pd.DataFrame) -> dict:
    try:
        engine = ForensicsEngine()
        engine.load_data(df)
        result = engine.run_all()
        graph_data = engine.get_graph_data()
        if "error" in result:
             return {"error": result["error"]}
        return {
            "result": json.loads(json.dumps(result, default=str)),
            "graph": json.loads(json.dumps(graph_data, default=str)),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/analyze")
async def analyze_private(file: UploadFile = File(...), current_user: dict = Depends(get_analyst_or_admin)):
    """
    Authenticated access. Returns full ML detail and decisions.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        from ingestor import DataIngestor
        df = DataIngestor.ingest(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    output = run_engine_safe(df)
    if "error" in output:
        raise HTTPException(status_code=500, detail=output["error"])
    return JSONResponse(content=output)


@app.post("/api/analyze/public")
async def analyze_public(file: UploadFile = File(...)):
    """
    Guest access. Strips ML details, roles, and flags.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        from ingestor import DataIngestor
        df = DataIngestor.ingest(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    output = run_engine_safe(df)
    if "error" in output:
        raise HTTPException(status_code=500, detail=output["error"])
        
    # Strip ML detail
    if "result" in output:
        for acc in output["result"].get("suspicious_accounts", []):
            acc.pop("role", None)
            acc.pop("decision", None)
            acc.pop("ml_scores", None)
            acc.pop("flag_hits", None)
            
    if "graph" in output:
        for node in output["graph"].get("nodes", []):
            node.pop("role", None)
            node.pop("decision", None)
            
    return JSONResponse(content=output)



# ---- Serve frontend static build ---- #
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for SPA routing."""
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
