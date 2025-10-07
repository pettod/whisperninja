import os
import argparse
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant


# Twilio credentials from environment variables
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
API_KEY = os.getenv("TWILIO_API_KEY")
API_SECRET = os.getenv("TWILIO_API_SECRET")
TWIML_APP_SID = os.getenv("TWIML_APP_SID")  # Create a TwiML App in Twilio

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Serve static files (like JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/token")
async def get_token():
    identity = "user"
    token = AccessToken(ACCOUNT_SID, API_KEY, API_SECRET, identity=identity)
    voice_grant = VoiceGrant(
        outgoing_application_sid=TWIML_APP_SID,
        incoming_allow=True
    )
    token.add_grant(voice_grant)
    return JSONResponse({"token": token.to_jwt()})

def main():
    parser = argparse.ArgumentParser(description="Voice agent API server")
    parser.add_argument("--global", dest="global_flag", action="store_true", help="Run server on 0.0.0.0 (accessible from other devices)")
    args = parser.parse_args()
    host = "0.0.0.0" if args.global_flag else "localhost"
    uvicorn.run(app, host=host, port=3000)

if __name__ == "__main__":
    main()