"""Start the Redevelopment DA Suite:  python run.py  [--port 8765]"""
import argparse

import uvicorn

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    uvicorn.run("dacore.api:app", host=a.host, port=a.port)
