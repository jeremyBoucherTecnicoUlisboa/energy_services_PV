import pandas as pd

from api import get_weather_data
from PVprod import estimate_pv_production
import matplotlib.pyplot as plt
import plotly


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
# Example usage:
    location = (52.52, 13.41)  # Latitude, Longitude
    start_date = ""  # Start date for archive data; not used for forecast
    end_date = ""  # Start date for archive data; not used for forecast
    # weather_df = get_weather_data(location, start_date, end_date, data_type="forecast")
    weather_df = pd.read_csv('forecast_weather.csv', parse_dates=['date'], index_col='date')
    pv_prod = estimate_pv_production(weather_df, location[0], location[1], 1, 0, 90)
    weather_df.to_csv('forecast_weather.csv')
    print(weather_df)
    print(pv_prod)
    plt.plot(pv_prod)
    plt.show()
    plt.plot(weather_df)
    plt.show()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
