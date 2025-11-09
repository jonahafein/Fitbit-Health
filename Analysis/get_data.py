from Azure_Database import database

sleep_raw = database()
sleep_df_raw = sleep_raw.query("SELECT * FROM sleep_raw order by dateOfSleep desc")
print(sleep_df_raw.head())
