"""Ponto de entrada na Azure Functions: entrega a mesma API FastAPI (app/main.py) ao Azure.

Localmente nada muda: continue usando `uvicorn app.main:app`.
"""
import azure.functions as func

from app.main import app as fastapi_app

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
