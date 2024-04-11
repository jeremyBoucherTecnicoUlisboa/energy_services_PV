import pandas as pd
import pvlib
import numpy as np
import matplotlib.pyplot as plt


def estimate_pv_production(df, latitude, longitude, capacity_kw, tilt, azimuth, gamma_pdc=-0.004):
    """
    Estimates PV production from solar irradiance data.

    Parameters:
    - df: DataFrame containing hourly GHI, DHI, and DNI.
    - latitude: Latitude of the location.
    - longitude: Longitude of the location.
    - tz: Timezone of the location.
    - capacity_kw: Capacity of the PV system in kW.
    - tilt: Tilt angle of the solar panels.
    - azimuth: Azimuth angle of the solar panels.
    - gamma_pdc: coef loss of power in function of temperature (divide by 100 to go from %/°C to 1/°C)

    Returns:
    - Series with estimated PV production in kW for each hour.
    """

    location_ = pvlib.location.Location(latitude=latitude, longitude=longitude)
    solar_position = location_.get_solarposition(df.index, temperature=df['temperature_2m'])
    poa = pvlib.irradiance.get_total_irradiance(surface_tilt=tilt,
                                                surface_azimuth=azimuth,
                                                solar_azimuth=solar_position['azimuth'],
                                                solar_zenith=solar_position['zenith'],
                                                dni=df['DNI'],
                                                dhi=df['DHI'],
                                                ghi=df['GHI'])

    parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_polymer']
    cell_temperature = pvlib.temperature.sapm_cell(poa['poa_global'],
                                                   df['temperature_2m'],
                                                   df['wind_speed_10m'],
                                                   **parameters)

    array_power = pvlib.pvsystem.pvwatts_dc(poa['poa_global'], cell_temperature, capacity_kw, gamma_pdc)
    array_power.rename("PV power [kW]", errors="raise", inplace=True)

    return array_power


def print_result(power, lat):
    energy_tot = np.sum(power)
    energy_day = energy_tot*24/len(power.index)
    best_tilt, best_azimuth = best_pv_angles(lat)

    return f"""
Total produced energy over this period : {energy_tot:.1f} kWh  
Average energy per day : {energy_day:.1f} kWh / day  
Max power produced : {power.max():.2e} kW at the {power.idxmax()}  

For this location the best angles are :  
    - Tilt = {best_tilt:.1f} °  
    - Azimuth = {best_azimuth:.1f} °  
    """


def best_pv_angles(latitude):
    """
    Calculate the best tilt and azimuth angle for a PV panel based on latitude.

    :param latitude: Latitude of the location in degrees. Positive for north, negative for south.
    :return: A tuple with the best tilt angle and azimuth angle. Azimuth is measured in degrees from true north,
             so 180 is true south, and 0 is true north.
    """

    best_tilt = min(abs(latitude), 90)

    if latitude > 0:
        best_azimuth = 180
    else:
        best_azimuth = 0

    return best_tilt, best_azimuth



