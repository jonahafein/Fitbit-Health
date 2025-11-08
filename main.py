from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates 
import requests, os, urllib, base64
import plotly.graph_objs as go
import uvicorn
import webbrowser
from datetime import date, timedelta
import pandas as pd
from Azure_Database import database
import config

# improve upon this later
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI  = config.REDIRECT_URI

# helper function for getting the mean bed time and wake up time

# maybe move these functions to another file or make some class
def get_time_min(time):
    if 0 <= time.hour < 12:
        hours = time.hour + 24
        minutes = time.minute
        totalMin = (hours*60) + minutes
        return totalMin
    else:
        hours = time.hour
        minutes = time.minute
        totalMin = (hours*60) + minutes
        return totalMin

# function to convert hour and min to a time
def getTime(Hour, Min):
    Hour = int(Hour)
    Min = int(Min)
    if 34 > Hour >= 24:
        Hour = Hour - 24
        if Min < 10:
            time = '0' + str(Hour) + ':' + '0' + str(Min)
        else:
            time = '0' + str(Hour) + ':' + str(Min)
    elif Hour >= 34:
        Hour = Hour - 24
        if Min < 10:
            time = str(Hour) + ':' + '0' + str(Min)
        else:
            time = str(Hour) + ':' + str(Min)
    else:
        if Min < 10:
            time = str(Hour) + ':' + '0' + str(min)
        else:
            time = str(Hour) + ':' + str(min)
    return time

# dates I am pulling data from
today = date.today()
hundred_days_ago = today - timedelta(days = 100)
seven_days_ago = today - timedelta(days = 7)
fourteen_days_ago = today - timedelta(days = 14)
month_ago = today - timedelta(days = 30)
first_day = '2025-09-29'

app = FastAPI()
template = Jinja2Templates(directory='templates')

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
    heart_df = database()
    heartRateDataFrameClean = heart_df.query("SELECT * FROM heart_data order by date desc")
    heartRateDataFrameClean['date'] = pd.to_datetime(heartRateDataFrameClean['date'])
    last_week_heart = heartRateDataFrameClean[heartRateDataFrameClean['date'] >= pd.to_datetime(seven_days_ago)]
    last_month_heart = heartRateDataFrameClean[heartRateDataFrameClean['date'] >= pd.to_datetime(month_ago)]
    
    last_week_heart_summary = round(last_week_heart[['cardioMinutes', 'fatBurnMinutes', 'normalMinutes',
                                             'peakMinutes', 'restingHR', 'dailyHRV', 'deepHRV']].describe(), 2)
    
    last_week_heart_summary = last_week_heart[['cardioMinutes', 'fatBurnMinutes', 'normalMinutes',
                                              'peakMinutes', 'restingHR', 'dailyHRV', 'deepHRV']].describe()
    last_week_heart_summary = last_week_heart_summary.transpose().reset_index()
    last_week_heart_summary['count'] = last_week_heart_summary['count'].astype(int)
    last_week_heart_summary = last_week_heart_summary.transpose()
    last_week_heart_summary.columns = last_week_heart_summary.iloc[0].to_list()
    last_week_heart_summary = last_week_heart_summary.iloc[1:]
    
    # sleep 
    sleep_df = database()
    sleep_dataframe =  sleep_df.query("SELECT * FROM sleep_data_raw order by dateOfSleep desc")
    sleep_dataframe_display = sleep_df.query("SELECT * FROM sleep_data_display order by dateOfSleep desc")
    
    # last week
    summary_sleep = sleep_dataframe.copy(deep = True)
    summary_sleep['dateOfSleep'] = pd.to_datetime(summary_sleep['dateOfSleep'])
    summary_sleep = summary_sleep[['dateOfSleep', 'isMainSleep', 'efficiency', 'minutesAsleep', 'minutesAwake', 'startTime', 'endTime']]
    summary_sleep = summary_sleep.rename(columns = {"efficiency": 'sleepScore',
                                                    'minutesAwake': 'timeAwake', 'minutesAsleep': 'timeAsleep'})
    
    # last week specific  
    last_week = summary_sleep[summary_sleep['dateOfSleep'] >= pd.to_datetime(seven_days_ago)]
    
    # get number of naps in the last week
    number_naps_lastWK = last_week[last_week['isMainSleep'] == False].shape[0]
    # print(number_naps_lastWK)
    
    # take out naps
    last_week = last_week[last_week['isMainSleep'] == True]
    
    # getting avg bed time last week
    count = 0
    timeMin = 0
    last_week['startTimeNoDate'] = pd.to_datetime(last_week['startTime']).dt.time
    for row in last_week['startTimeNoDate']:
        timeMin = timeMin + get_time_min(row)
        count = count + 1

    avgBedtimeHourLastWK = (timeMin/count)//60
    avgBedtimeMinLastWK = (timeMin/count)%60
    
    avgBedtimeLastWk = getTime(avgBedtimeHourLastWK, avgBedtimeMinLastWK)
    
    # getting average wakeup time
    count = 0
    timeMin = 0
    last_week['endTimeNoDate'] = pd.to_datetime(last_week['endTime']).dt.time
    for row in last_week['endTimeNoDate']:
        timeMin = timeMin + get_time_min(row)
        count = count + 1
        
    avgWakeupHourLastWK = (timeMin/count)//60
    avgWakeupMinLastWK = (timeMin/count)%60
    
    avgWakeupLastWk = getTime(avgWakeupHourLastWK, avgWakeupMinLastWK)
    
    last_week_summary = last_week.describe()
    last_week_summary['timeAsleep'] = pd.to_datetime(last_week_summary['timeAsleep'], unit = 'm').dt.strftime("%H:%M")
    last_week_summary['timeAwake'] = pd.to_datetime(last_week_summary['timeAwake'], unit = 'm').dt.strftime("%H:%M")
    
    # dropping date and count
    last_week_summary = round(last_week_summary.drop(columns = ['dateOfSleep']).drop(index = last_week_summary.index[0]), 2)
    
    # last month specific
    last_month = summary_sleep[summary_sleep['dateOfSleep'] >= pd.to_datetime(month_ago)]
    
    # number of naps last month
    number_naps_lastMonth = last_month[last_month['isMainSleep'] == False].shape[0]
    # print(number_naps_lastMonth)
    
    # take out naps
    last_month = last_month[last_month['isMainSleep'] == True]
    
    # getting avg bed time last month
    count = 0
    timeMin = 0
    last_month['startTimeNoDate'] = pd.to_datetime(last_month['startTime']).dt.time
    for row in last_month['startTimeNoDate']:
        timeMin = timeMin + get_time_min(row)
        count = count + 1

    avgBedtimeHourLastMonth = (timeMin/count)//60
    avgBedtimeMinLastMonth = (timeMin/count)%60
    
    avgBedtimeLastMonth = getTime(avgBedtimeHourLastMonth, avgBedtimeMinLastMonth) 
    
    # getting avg wakeup time past month
    count = 0
    timeMin = 0
    last_month['endTimeNoDate'] = pd.to_datetime(last_month['endTime']).dt.time
    for row in last_month['endTimeNoDate']:
        timeMin = timeMin + get_time_min(row)
        count = count + 1
        
    avgWakeupHourLastMonth = (timeMin/count)//60
    avgWakeupMinLastMonth = (timeMin/count)%60
    
    avgWakeupLastMonth = getTime(avgWakeupHourLastMonth, avgWakeupMinLastMonth)  
    
    last_month_summary = last_month.describe()
    last_month_summary['timeAsleep'] = pd.to_datetime(last_month_summary['timeAsleep'], unit = 'm').dt.strftime("%H:%M")
    last_month_summary['timeAwake'] = pd.to_datetime(last_month_summary['timeAwake'], unit = 'm').dt.strftime("%H:%M")
    
    # dropping date and count
    last_month_summary = round(last_month_summary.drop(columns = ['dateOfSleep']).drop(index = last_month_summary.index[0]), 2)
    
    return template.TemplateResponse(
        'dashboard.html',
        {'request': request, 
         'sleep_data': sleep_dataframe_display.to_html(),
         'last_week_summary': last_week_summary.to_html(),
         'last_month_summary': last_month_summary.to_html(),
         'avg_bedtime_last_week': avgBedtimeLastWk,
         'avg_bedtime_last_month': avgBedtimeLastMonth,
         'avgWakeupLastWK': avgWakeupLastWk,
         'avgWakeupLastMonth': avgWakeupLastMonth,
         'heartDataFrame': heartRateDataFrameClean.to_html(),
         'napsLastWK': number_naps_lastWK,
         'napsLastMonth': number_naps_lastMonth}
    )

if __name__ == "__main__":
    webbrowser.open(url = 'http://127.0.0.1:8000') 
    uvicorn.run(app, host="127.0.0.1", port=8000)  
    webbrowser.open(url = 'http://127.0.0.1:8000/dashboard')
    

