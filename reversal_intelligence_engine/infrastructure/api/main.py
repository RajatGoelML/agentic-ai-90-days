# ================================
# API Layer — Reversal Intelligence Engine
# ================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import sys, os, json, glob, time

# infrastructure/api/main.py is 2 levels deep — go up 3 to reach reversal_intelligence_engine/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from engine.state.state_model import initialize_state
from engine.scheduler import get_next_nodes
from engine.executor import execute_nodes_in_parallel
from engine.utils.state_updater import apply_node_result
from reversal_strategy.registry.node_registry import NODE_REGISTRY
from reversal_strategy.graph.graph_config import GRAPH

app = FastAPI(title="Reversal Intelligence Engine")

# =============================================
# CORS — allow frontend requests
# =============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# Paths
# =============================================
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
WATCHLIST_DIR = os.path.join(BASE_DIR, "data", "outputs", "watchlist")


# =============================================
# API — Run Workflow
# =============================================
@app.post("/run-workflow")
def run_workflow_api():
    state = initialize_state()
    execution_log = []

    while True:
        next_nodes = get_next_nodes(GRAPH, state["completed_nodes"])
        if not next_nodes:
            break
        t0 = time.time()
        results = execute_nodes_in_parallel(next_nodes, NODE_REGISTRY, state)
        elapsed = round(time.time() - t0, 2)
        for item in results:
            node_name = item["node"]
            if item["success"]:
                apply_node_result(state, item["result"])
                execution_log.append({
                    "node":     node_name,
                    "status":   "SUCCESS",
                    "duration": elapsed,
                })
            else:
                execution_log.append({
                    "node":     node_name,
                    "status":   "FAILED",
                    "duration": elapsed,
                    "error":    item.get("error", ""),
                })
            state["completed_nodes"].add(node_name)

    # Inject execution_log into run_latest.json so history loads also show it
    latest_file = os.path.join(WATCHLIST_DIR, "run_latest.json")
    if os.path.exists(latest_file):
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["execution_log"] = execution_log
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return data
        except Exception:
            pass

    # Fallback: return raw state if file read fails
    return {
        "generated_at": None,
        "stocks_analyzed": len(state.get("final_recommendations", [])),
        "token_usage": state.get("token_usage"),
        "recommendations": state.get("final_recommendations", []),
        "execution_log": execution_log,
    }


# =============================================
# API — Load Latest Watchlist
# =============================================
@app.get("/api/watchlist/latest")
def get_latest_watchlist():
    if not os.path.exists(WATCHLIST_DIR):
        return JSONResponse(
            content={"recommendations": [], "message": "No watchlist directory found"},
            status_code=200
        )

    # Prefer run_latest.json (always written by WatchlistNode after every run)
    latest_symlink = os.path.join(WATCHLIST_DIR, "run_latest.json")
    if os.path.exists(latest_symlink):
        latest = latest_symlink
    else:
        # Fallback: pick the newest dated run file
        run_files = sorted(glob.glob(os.path.join(WATCHLIST_DIR, "*_run_*.json")))
        if not run_files:
            return JSONResponse(
                content={"recommendations": [], "message": "No watchlist files found"},
                status_code=200
            )
        latest = run_files[-1]

    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        with open(latest, "r", encoding="cp1252") as f:
            data = json.load(f)
    return data


# =============================================
# API — List Watchlist History
# =============================================
@app.get("/api/watchlist/history")
def get_watchlist_history():
    if not os.path.exists(WATCHLIST_DIR):
        return {"files": []}
    # Return dated run files only (exclude run_latest.json alias)
    files = sorted(
        glob.glob(os.path.join(WATCHLIST_DIR, "*_run_*.json")),
        reverse=True
    )
    return {"files": [os.path.basename(f) for f in files]}


# =============================================
# API — Load Specific Watchlist File
# =============================================
@app.get("/api/watchlist/{filename}")
def get_watchlist_file(filename: str):
    filepath = os.path.join(WATCHLIST_DIR, filename)
    if not os.path.exists(filepath):
        return JSONResponse(content={"error": "File not found"}, status_code=404)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="cp1252") as f:
            data = json.load(f)
    return data


# =============================================
# Frontend — Serve index.html at root
# =============================================
@app.get("/")
def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(content={"error": "Frontend not found"}, status_code=404)


# =============================================
# Frontend — Serve static files (css, js)
# =============================================
if os.path.exists(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
