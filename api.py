import requests_cache
import pandas as pd
from retry_requests import retry
import openmeteo_requests
import requests
from geopy.geocoders import Nominatim


def get_weather_data(location, start_date, end_date=None, variables=["temperature_2m", "wind_speed_10m","diffuse_radiation", "direct_normal_irradiance", "global_tilted_irradiance"], data_type="forecast"):
    """
    Fetches weather data or forecast for a specified location and time range, and returns it as a pandas DataFrame.

    Parameters:
    - location: tuple of (latitude, longitude)
    - start_date: string in "YYYY-MM-DD" format representing the start date
    - end_date: string in "YYYY-MM-DD" format representing the end date (optional, mainly for archive data)
    - variables: list of strings representing the weather variables to retrieve
    - data_type: string specifying the type of data ("archive" for historical data, "forecast" for future data)

    Returns:
    - pandas DataFrame containing the weather data
    """
    # Setup the Open-Meteo API client with cache and retry on error
    cache_expire_after = 3600 if data_type == "forecast" else -1  # Shorter cache duration for forecasts
    cache_session = requests_cache.CachedSession('.cache', expire_after=cache_expire_after)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Select the appropriate API URL based on the data type
    url = "https://api.open-meteo.com/v1/forecast" if data_type == "forecast" else "https://archive-api.open-meteo.com/v1/archive"

    # Prepare API request parameters
    params = {
        "latitude": location[0],
        "longitude": location[1],
        "hourly": ",".join(variables)
    }
    if data_type == "archive":
        params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
    # Fetch the weather data
    responses = openmeteo.weather_api(url, params=params)

    # Process the first (and potentially only) location
    response = responses[0]

    # Process hourly data
    hourly = response.Hourly()
    hourly_data = {"date": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )}

    # Add each requested variable to the hourly data dictionary
    for i, var in enumerate(variables):
        hourly_data[var] = hourly.Variables(i).ValuesAsNumpy()

    # Convert the data to a pandas DataFrame and return
    hourly_dataframe = pd.DataFrame(data=hourly_data)
    if 'date' in hourly_dataframe.columns:
        hourly_dataframe.set_index('date',inplace=True)

    hourly_dataframe.rename(columns={"diffuse_radiation": "DHI", "direct_normal_irradiance": "DNI", "global_tilted_irradiance": "GHI"}, errors="raise", inplace=True)

    return hourly_dataframe


# Define a function to find the nearest city and country using Nominatim API
def find_nearest_city_country(latitude, longitude):
    try :
        # Initialize Nominatim API
        geo_locator = Nominatim(user_agent="geoapiExercises")

        # Use the reverse method to find the address from latitude and longitude
        location = geo_locator.reverse((latitude, longitude), exactly_one=True)

        # Extract address details
        address = location.raw['address']
        country = address.get('country', 'Country not found')
        city = address.get('city', address.get('town', 'City not found'))
    except :
        country = 'Country not found'
        city = 'City not found'

    return city, country


