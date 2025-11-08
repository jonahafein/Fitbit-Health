import pandas as pd
from azure import identity
import struct, pyodbc

# all azure connections will be made in here eventually
class database:
    def __init__(self):
        self.connection_string = "Driver=/opt/homebrew/lib/libmsodbcsql.18.dylib;Server=tcp:healthmetricsserver.database.windows.net,1433;Database=Health_Metrics;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        
    # method needed to connect for other methods
    def get_conn(self):
        credential = identity.DefaultAzureCredential(exclude_interactive_browser_credential = False)
        token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
        token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
        SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h
        conn = pyodbc.connect(self.connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        return conn

    # returns result of the query
    def query(self, query: str, print_results = False):
        conn = self.get_conn()
        cursor = conn.cursor()
        print("Connecting to Azure:")
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        df = pd.DataFrame((tuple(t) for t in rows))
        # build the columns for the dataframe
        if "sleep_data_display" in query:
            columns = ['dateOfSleep', 'infoCode', 'sleepScore', 'startTime', 'endTime', 'isMainSleep', 'timeAsleep', 'timeAwake']
            df.columns = columns
        elif "sleep_data_raw" in query:
            columns = ['dateOfSleep', 'duration', 'efficiency', 'startTime', 'endTime','infoCode', 'isMainSleep', 'levels', 'logId', 'minutesAfterWakeup','minutesAwake', 'minutesAsleep', 'minutesToFallAsleep', 'logType','timeInBed', 'type']
            df.columns = columns
        elif "heart_data" in query:
            columns = ['date', 'cardioMinutes', 'fatBurnMinutes', 'normalMinutes', 'peakMinutes', 'restingHR', 'dailyHRV', 'deepHRV']
            df.columns = columns
        elif "sample_data" in query:
            columns = ['Id', 'Name', 'Mobile']
            df.columns = columns
        else:
            print("Error: Incorrect table name.")
            return None
        if print_results == True:
            print(df)
        return pd.DataFrame(df)

      
    # adds data to specific table in azure database  
    def add_to_azure(self, table, data:pd.DataFrame):
        conn = self.get_conn()
        cursor = conn.cursor()
        if table == "sample_table":
            for index, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table} (Id, Name, Mobile) VALUES (?, ?, ?)", row.Id, row.Name, row.Mobile)
                cursor.commit()
            cursor.close()
        elif table == "sleep_data_display":
            for index, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table}(dateOfSleep, infoCode, sleepScore, startTime, endTime, isMainSleep, timeAsleep, timeAwake) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row.dateOfSleep, row.infoCode, row.sleepScore, row.startTime, row.endTime, row.isMainSleep, row.timeAsleep, row.timeAwake)
                cursor.commit()
            cursor.close()
        elif table == "sleep_data_raw":
            for index, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table}(dateOfSleep, duration, efficiency, startTime, endTime, infoCode, isMainSleep, minutesAfterWakeup, minutesAwake, minutesAsleep, minutesToFallAsleep, timeInBed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row.dateOfSleep, row.duration, row.efficiency, row.startTime, row.endTime, row.infoCode, row.isMainSleep, row.minutesAfterWakeup, row.minutesAwake, row.minutesAsleep, row.minutesToFallAsleep, row.timeInBed)
                cursor.commit()
            cursor.close()
        elif table == "heart_data":
            for index, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table}(date, cardioMinutes, fatBurnMinutes, normalMinutes, peakMinutes, restingHR, dailyHRV, deepHRV) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row.date, row.cardioMinutes, row.fatBurnMinutes, row.normalMinutes, row.peakMinutes, row.restingHR, row.dailyHRV, row.deepHRV)
                cursor.commit()
            cursor.close()
        else:
            print("Error: Incorrect table name")






