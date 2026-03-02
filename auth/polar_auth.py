import requests
import os
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

ENV_PATH = "/home/datascientest/cde/polar/.env"
load_dotenv(ENV_PATH)

CLIENT_ID = os.getenv("POLAR_CLIENT_ID")
CLIENT_SECRET = os.getenv("POLAR_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8089/oauth2_callback"
AUTH_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"

# Ouvre le navigateur pour autoriser
auth_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
print(f"Ouvre ce lien : {auth_url}")
webbrowser.open(auth_url)

# Capture le code de retour
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        code = params.get("code", [None])[0]
        if code:
            print(f"\nCode reçu : {code}")
            response = requests.post(TOKEN_URL,
                auth=(CLIENT_ID, CLIENT_SECRET),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI
                }
            )
            token = response.json()
            print(f"Token complet : {token}")
            with open(ENV_PATH, "a") as f:
                f.write(f"\nPOLAR_ACCESS_TOKEN={token.get('access_token')}")
                f.write(f"\nPOLAR_USER_ID={token.get('x_user_id')}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK, tu peux fermer cette fenetre")

HTTPServer(("localhost", 8089), Handler).handle_request()