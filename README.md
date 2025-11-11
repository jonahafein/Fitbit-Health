# Fitbit-Health
Using the Fitbit API to create a custom dashboard that will include personalized predictions, analytics, and insights.

## Next Steps:
- Logic for daily updates to the Azure Database
- Write main to host the dashboard + add analytics to it
- Pull more data
- Create models and insights

Eventually, data will be pulled automatically from Azure into the models/insights. However, as I create the models and analysis I don't want to exhaust compute, so for now I will opt to create csv's to be used in the meantime.

## Ideas:
- Make Fitbit_API a class to make main and API call more readable -- Add methods for adding data, pulling data, etc for more functionality.
