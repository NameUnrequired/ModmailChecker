import os
import requests
import webbrowser
from urllib.parse import urlencode
from flask import Flask, request

# -----------------
# CONFIGURATION
# -----------------
CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDIRECT_URI  = os.environ.get("REDDIT_REDIRECT_URI", "http://localhost:8080/callback")
SUBREDDIT     = os.environ.get("SUBREDDIT_NAME", "yoursubreddit")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in environment")

USER_AGENT = "python:modmail.checker:v1.0 (by /u/yourusername)"

# -----------------
# SERVER FOR OAUTH
# -----------------
app = Flask(__name__)
AUTH_CODE = None

@app.route("/callback")
def callback():
    global AUTH_CODE
    AUTH_CODE = request.args.get("code")
    return "Authorization received! Close this window and return to terminal."

def get_authorization():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "state": "random_state_123",
        "redirect_uri": REDIRECT_URI,
        "duration": "temporary",
        "scope": "modmail read"
    }
    url = "https://www.reddit.com/api/v1/authorize?" + urlencode(params)
    print("Visit this URL to authorize:")
    print(url)
    webbrowser.open(url)

def fetch_access_token(auth_code):
    token_url = "https://www.reddit.com/api/v1/access_token"
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"User-Agent": USER_AGENT}
    resp = requests.post(token_url, auth=auth, data=data, headers=headers)
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_modmail_conversations(access_token):
    api_url = "https://oauth.reddit.com/api/mod/conversations"
    headers = {
        "Authorization": f"bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "entity": SUBREDDIT,
        "sort": "unread",  # only unread or recent
        "limit": 10
    }
    resp = requests.get(api_url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

# -----------------
# MAIN FLOW
# -----------------
if __name__ == "__main__":
    # 1) Ask user to authorize
    get_authorization()

    # 2) Run a temporary local server to receive callback
    print("Waiting for authorization callback on http://localhost:8080/callback …")
    app.run(port=8080, debug=False, use_reloader=False)

    if not AUTH_CODE:
        raise RuntimeError("Authorization failed or timed out")

    # 3) Exchange code for token
    token = fetch_access_token(AUTH_CODE)

    # 4) Query modmail
    data = get_modmail_conversations(token)
    conversations = data.get("conversations", [])

    if conversations:
        print(f"📬 Found {len(conversations)} modmail threads!")
        for convo in conversations:
            print(" *", convo.get("conversation_id"))
    else:
        print("✅ No modmail found right now.")
