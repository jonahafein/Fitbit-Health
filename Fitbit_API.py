from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates 
import requests, os, urllib, base64
import plotly.graph_objs as go
import uvicorn
from uvicorn.config import Config
import webbrowser
import time
from datetime import date, timedelta
import pandas as pd
import threading
from server import Server
import subprocess

today = date.today()
hundred_days_ago = today - timedelta(days = 100)
seven_days_ago = today - timedelta(days = 7)
fourteen_days_ago = today - timedelta(days = 14)
month_ago = today - timedelta(days = 30)
first_day = '2025-09-29'

app = FastAPI()
template = Jinja2Templates(directory='templates2')

# improve upon this later
CLIENT_ID = '23TGR4'
CLIENT_SECRET = '1fd8731d5b695bc06543916997fea755'
REDIRECT_URI  = 'http://localhost:8000/callback'

global user_tokens 
user_tokens = {}

@app.get('/')
def login():
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'activity cardio_fitness heartrate location respiratory_rate sleep temperature weight'
    }
    
    url = "https://www.fitbit.com/oauth2/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@app.get('/callback')
def callback(code:str):
    token_url = 'https://api.fitbit.com/oauth2/token' # base url is api.fitbit.com and oauth2/token' is authorization endpoint
    headers = {
        'Authorization': f'Basic {get_basic_auth_token()}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'client_id': CLIENT_ID,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'code': code,
    }
    
    response = requests.post(token_url, headers = headers, data = data)
    tokens = response.json() 
    user_tokens['access_token'] = tokens['access_token']
    user_tokens['user_id'] = tokens['user_id']
    return RedirectResponse(url = '/dashboard')

def get_basic_auth_token():
    return base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

@app.get('/dashboard')
def dashboard(request: Request):
    access_token = user_tokens.get('access_token')
    if not access_token:
        print("doing authentication again")
        return RedirectResponse('/') # does authentication all over again
    
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    
    # user_id = user_tokens['user_id']
    
    # heart rate data 
    heart_url = f'https://api.fitbit.com/1/user/-/activities/heart/date/{month_ago}/{today}/1min.json'
    heart_response = requests.get(heart_url, headers = headers)
    heartRateData = heart_response.json()
    heartRateData = heartRateData.get('activities-heart')
    print(heartRateData)

if __name__ == "__main__":
    config = Config(app = app, host="127.0.0.1", port=8000, log_level = "info")
    server = Server(config = config)
    # run and automatically stop server
    with server.run_in_thread():
        print("uvicorn server started")
        webbrowser.open(url = 'http://127.0.0.1:8000')
        time.sleep(3)
        print("stopping uvicorn server")
    print("uvicorn server stopped")