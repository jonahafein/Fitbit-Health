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
    def query(self, query: str):
        conn = self.get_conn()
        cursor = conn.cursor()
        print("Connecting to Azure:")
        cursor.execute(query)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        print(df)
        #conn.close()
        #cursor.close()
      
    # adds data to specific table in azure database  
    def add_to_azure(self, table, data:pd.DataFrame):
        conn = self.get_conn()
        cursor = conn.cursor()
        if table == "sample_table":
            for index, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table} (Id, Name, Mobile) VALUES (?, ?, ?)", row.Id, row.Name, row.Mobile)
                cursor.commit()
            cursor.close()
        if table == "sleep_data":
            for index, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table}(dateOfSleep, infoCode, sleepScore, startTime, endTime, isMainSleep, timeAsleep, timeAwake) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row.dateOfSleep, row.infoCode, row.sleepScore, row.startTime, row.endTime, row.isMainSleep, row.timeAsleep, row.timeAwake)
                cursor.commit()
            cursor.close()
        if table == "heart_data":
            for index, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table}(date, cardioMinutes, fatBurnMinutes, normalMinutes, peakMinutes, restingHR, dailyHRV, deepHRV) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row.date, row.cardioMinutes, row.fatBurnMinutes, row.normalMinutes, row.peakMinutes, row.restingHR, row.dailyHRV, row.deepHRV)
                cursor.commit()
            cursor.close()

 # testing
        
# initial query      
# df = database()
# df.query("SELECT * FROM sample_table")

# # sample data to add
# sample_data = {'Id': [3], 'Name': ['Gershona'], 'Mobile': ['6174475147']}
# sample_dataframe = pd.DataFrame(sample_data)
# for inx,row in sample_dataframe.iterrows():
#     print(row)
# print()

# # add data into azure
# df.add_to_azure(table = "sample_table", data = sample_dataframe)
# # make sure it was added
# df.query("SELECT * FROM sample_table")

# df = database()
# sample_data = {'Id': [6], 'Name': ['Blair'], 'Mobile': ['9076134899']}
# sample_dataframe = pd.DataFrame(sample_data)
# df.add_to_azure(table = "sample_table", data = sample_dataframe)

# testing from our data
# df.query("SELECT * FROM heart_data order by date desc")
# df.query("SELECT * FROM sleep_data order by dateOfSleep desc")






