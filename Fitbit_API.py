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
from Azure_Database import database

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
        return RedirectResponse('/') # does authentication all over again
    
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    
    # user_id = user_tokens['user_id']
    
    # heart rate data 
    heart_url = f'https://api.fitbit.com/1/user/-/activities/heart/date/2025-10-30/{today}/1min.json'
    heart_response = requests.get(heart_url, headers = headers)
    heartRateData = heart_response.json()
    heartRateData = heartRateData.get('activities-heart')
    
    # building the heartrate dataframe
    heartRateDataFrame = pd.DataFrame()
    for day in heartRateData:
        for zone in day.get('value').get('heartRateZones'):
            zone_df = pd.DataFrame(zone, index = [i for i in range(0, len(day.get('value').get('heartRateZones')))])
            zone_df['date'] = day.get('dateTime')
            zone_df['restingHR'] = day.get('value').get('restingHeartRate')
            heartRateDataFrame = pd.concat([heartRateDataFrame, zone_df], ignore_index = True)
            
    heartRateDataFrame_sum = heartRateDataFrame.groupby(['date', 'name'])[['minutes']].sum().reset_index().set_index(['date', 'name']).unstack("name").reset_index()
    heartRateDataFrame_sum.columns = ['date', 'Cardio Minutes', 'Fat Burn Minutes', 'Out of Range Minutes', 'Peak Minutes']
    heartRateDataFrame_sum['date'] = pd.to_datetime(heartRateDataFrame_sum['date'])
    heartRateDataFrame_sum = heartRateDataFrame_sum.sort_values(by = "date", ascending = False).reset_index().drop(columns = ['index'])
    heartRateDataFrame_sum[['Cardio Minutes', 'Fat Burn Minutes', 'Out of Range Minutes', 'Peak Minutes']] = heartRateDataFrame_sum[['Cardio Minutes', 'Fat Burn Minutes', 'Out of Range Minutes', 'Peak Minutes']].astype(int)
    heartRateDataFrame_sum = heartRateDataFrame_sum[heartRateDataFrame_sum['Out of Range Minutes'] != 0]
    
    dateSet = set(heartRateDataFrame['date'].to_list())
    dateList = list(dateSet)   
    
    restingHRS = []
    
    for date in dateList:
        Date_HR = heartRateDataFrame[heartRateDataFrame['date'] == str(date)].get('restingHR').to_list()[0]
        restingHRS.append(Date_HR)
      
    # creating the clean dataframe showing resting HR
    heartRateDataFrameClean = pd.DataFrame(list(zip(dateList, restingHRS)))
    heartRateDataFrameClean.columns = ['date', 'restingHR']
    heartRateDataFrameClean['date'] = pd.to_datetime(heartRateDataFrameClean['date'])
    heartRateDataFrameClean = heartRateDataFrameClean.sort_values(by = ['date'], ascending = False).dropna(subset = ['restingHR'])
    heartRateDataFrameClean['restingHR'] = heartRateDataFrameClean['restingHR'].astype("int")
    
    # join the 2 heart rate dataframes together
    heartRateDataFrameClean = heartRateDataFrame_sum.merge(heartRateDataFrameClean,how = 'left', on = 'date')
    heartRateDataFrameClean = heartRateDataFrameClean.rename(columns = {'Cardio Minutes': 'cardioMinutes', 'Fat Burn Minutes': 'fatBurnMinutes',
                                                                        'Out of Range Minutes': 'normalMinutes', 'Peak Minutes': 'peakMinutes'}) 
    
    # add in HRV to the data frame
    url = f"https://api.fitbit.com/1/user/-/hrv/date/2025-10-30/{today}.json"
    HRV = requests.get(url, headers = headers).json()
    dates = []
    dailyRmssd = []
    deepRmssd = []
    for day in range(0, len(HRV.get('hrv'))):
        dates.append(HRV.get('hrv')[day].get('dateTime'))
        dailyRmssd.append(HRV.get('hrv')[day].get('value').get('dailyRmssd'))
        deepRmssd.append(HRV.get('hrv')[day].get('value').get('deepRmssd'))
    
    HRVdf = pd.DataFrame(list(zip(dates, dailyRmssd, deepRmssd)))
    HRVdf.columns = ['date','dailyRmssd', 'deepRmssd']
    HRVdf['date'] = pd.to_datetime(HRVdf['date'])
    HRVdf = HRVdf.sort_values(by = "date", ascending = False)
    
    # merge HRV to other heart stats
    heartRateDataFrameClean = heartRateDataFrameClean.merge(HRVdf, how = 'left', on = 'date')
    heartRateDataFrameClean['dailyRmssd'].fillna(heartRateDataFrameClean['dailyRmssd'].mean(), inplace = True)
    heartRateDataFrameClean['deepRmssd'].fillna(heartRateDataFrameClean['deepRmssd'].mean(), inplace = True)
    heartRateDataFrameClean[['dailyRmssd', 'deepRmssd']] = heartRateDataFrameClean[['dailyRmssd', 'deepRmssd']].round(2)
    heartRateDataFrameClean = heartRateDataFrameClean.rename(columns = {'dailyRmssd': 'dailyHRV', 'deepRmssd': 'deepHRV'})
    
    # print(heartRateDataFrameClean)
    
    # add heart data to azure
    # heart_data_for_azure = database()
    # heart_data_for_azure.add_to_azure(table = "heart_data", data = heartRateDataFrameClean)
    
    # sleep data
    sleep_url = f'https://api.fitbit.com/1.2/user/-/sleep/date/2025-10-29/{today}.json'
    sleep_response = requests.get(sleep_url, headers = headers)
    sleep_dataframe = pd.DataFrame(sleep_response.json().get('sleep', {}))
    sleep_dataframe_display = sleep_dataframe[['dateOfSleep', 'infoCode',
                                       'efficiency', 'startTime', 
                                       'endTime', 'isMainSleep', 
                                       'minutesAwake', 'minutesAsleep']]
    sleep_dataframe = sleep_dataframe.drop(columns = ['levels', 'logId', 'logType', 'type'])
    sleep_dataframe['startTime'] = pd.to_datetime(sleep_dataframe['startTime']).dt.strftime('%Y-%m-%d %H:%M')
    sleep_dataframe['endTime'] = pd.to_datetime(sleep_dataframe['endTime']).dt.strftime('%Y-%m-%d %H:%M')

    #               Future Enhancements:
    # could include a key to variable meanings on the site
    # could add levels back in but will need to parse results out
    
    # data wrangling
    sleep_dataframe_display = sleep_dataframe_display.rename(columns = {'efficiency': 'sleepScore'})
    sleep_dataframe_display['timeAsleep'] = pd.to_datetime(sleep_dataframe_display['minutesAsleep'], 
                                                               unit = "m").dt.strftime("%H:%M").astype(str)
    sleep_dataframe_display['timeAwake'] = pd.to_datetime(sleep_dataframe_display['minutesAwake'], 
                                                               unit = "m").dt.strftime("%H:%M").astype(str)
    sleep_dataframe_display = sleep_dataframe_display.drop(columns = ['minutesAsleep', 'minutesAwake'])

    sleep_dataframe_display['startTime'] = pd.to_datetime(sleep_dataframe_display['startTime']).dt.strftime('%Y-%m-%d %H:%M')
    sleep_dataframe_display['endTime'] = pd.to_datetime(sleep_dataframe_display['endTime']).dt.strftime('%Y-%m-%d %H:%M')
    
    
    # add sleep data raw to azure
    sleep_data_raw = database()
    sleep_data_raw.add_to_azure(table = "sleep_data_raw", data = sleep_dataframe)
    
    # add sleep display data to azure
    # sleep_data_display = database()
    # sleep_data_display.add_to_azure(table = "sleep_data_display", data = sleep_dataframe_display)
    

if __name__ == "__main__":
    config = Config(app = app, host="127.0.0.1", port=8000, log_level = "info")
    server = Server(config = config)
    with server.run_in_thread(): # run and automatically stop server
        print("uvicorn server started")
        webbrowser.open(url = 'http://127.0.0.1:8000')
        time.sleep(20)
        print("stopping uvicorn server")
    print("uvicorn server stopped")