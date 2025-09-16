from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests

def verifygtoken(token: str):
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request())
        return idinfo
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Google token")
