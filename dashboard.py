from dash import Dash, html, Output, Input, dcc, State, callback, no_update
import dash_leaflet as dl
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from datetime import date
import pandas as pd
import plotly.express as px  # Import Plotly Express
from dash_extensions.javascript import assign
from PVprod import estimate_pv_production, print_result, best_pv_angles
from api import get_weather_data, find_nearest_city_country
from style_sheet import *
from datetime import date
import numpy as np


eventHandlers = dict(
    dblclick=assign("function(e, ctx){ctx.setProps({data: e.latlng})}")
)

# Then you use these styles in your Dash component definition as before.

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'PV Gen'
server = app.server

app.layout = html.Div([
    dl.Map([
        dl.TileLayer(),
        dl.ScaleControl(position="bottomleft"),
    ], doubleClickZoom=False, scrollWheelZoom=False, eventHandlers=eventHandlers, center=[38.71, -9.14], zoom=6, style={'height': '70vh'}, id="map"),

    # loc button
    html.Div([
        dmc.Title("Location", order=2, style=style_title),
        dmc.Text("Enter latitude and longitude of the PV plant or double click on the map. ", style=style_text),
        dmc.Container([
            dmc.TextInput(id="lat-input", type="number", placeholder='Latitude', style=style_input),
            dmc.TextInput(id="lon-input", type="number", placeholder='Longitude', style=style_input),
        ], style=flex_container_style),
        dmc.Button("Fly to Coordinates", id="btn", style=style_btn)
    ], style=style_cont),

    # weather button
    html.Div([
        dmc.Title("Weather", order=2, style=style_title),
        dcc.Markdown("Select the date for the computation.", style=style_text),
        dcc.Markdown(id='log_out', style=style_text),
        dcc.DatePickerRange(
            id='weather_date_range',
            min_date_allowed='2020-01-01',
            max_date_allowed=date.today().strftime("%Y-%m-%d"),
            initial_visible_month=date.today().strftime("%Y-%m-%d"),
            style={'margin': '5px auto','textAlign': 'center','display': 'block'}
        ),
        dmc.Checkbox(label='Forecast for the next days',id='forecast'),
        dmc.Button("Load data", id="btn_call_api", style=style_btn),
    ], style=style_cont),

    # weather graph
    html.Div([
        dcc.Graph(
            id='weather_graph',
            # figure=fig  # Assuming fig is defined elsewhere in your code
        )
    ]),

    # PV prod buttons
    html.Div([
        dmc.Title("PV panel configuration", order=2, style=style_title),
        dmc.Text("Enter the tilt and azimuth angle of your PV panel as well as the rated power in kW. If None horizontal plan and 1kW.", style=style_text),
        dmc.Container([
            dmc.TextInput(id="azimuth-input", type="number", placeholder='Azimuth', style=style_input),
            dmc.TextInput(id="tilt-input", type="number", placeholder='Tilt', style=style_input),
            dmc.TextInput(id="power-input", type="number", placeholder='Power', style=style_input),
        ], style=flex_container_style),
        dmc.Button("PV production", id="btn_PV_prod", style=style_btn)
    ], style=style_cont),

    # PV prod result
    html.Div([
        dmc.Title("PV panel results", order=2, style=style_title),
        dcc.Markdown(style=style_text,
            id='text_result'),
    ], style=style_cont),

    # PV prod graph
    html.Div([
        dcc.Graph(
            id='PV_graph',
            # figure=fig  # Assuming fig is defined elsewhere in your code
        )
    ]),

    # download
    html.Div([
        dmc.Title("Download data as csv files", order=3, style=style_title),
        dmc.Container([
            dmc.Button("Download Weather", id="btn_dl_weather", variant="outline"),
            dcc.Download(id="download_weather"),
            dmc.Button("Download Power", id="btn_dl_power", variant="outline"),
            dcc.Download(id="download_power"),
        ], style= {
    'display': 'flex',
    'flexDirection': 'row',  # Align children in a row
    'alignItems': 'center',  # Align items at the start of the flex container
    'gap': '20px',  # Space between the containers
}),
    ], style=style_cont),

])


@app.callback(Output("map", "viewport"),
              [Input("btn", "n_clicks")],
              [State("lat-input", "value"), State("lon-input", "value")],
              prevent_initial_call=True)
def fly_to_coordinates(_, lat, lon):
    if lat is not None and lon is not None:
        return {"center": [lat, lon], "zoom": 12, "transition": "flyTo"}


# New callback for displaying the selected date range
@app.callback(Output("weather_graph", "figure"),
              Output("log_out", "children"),
              [Input("btn_call_api", "n_clicks")],
              [State("weather_date_range", "start_date"),
               State("weather_date_range", "end_date"),
               State("lat-input", "value"),
               State("lon-input", "value"),
               State("forecast", "checked")],
              prevent_initial_call=True)
def display_date_range(_, start_date, end_date, lat, lon, forecast):
    if forecast:
        weather_df = get_weather_data((lat, lon), start_date, end_date=end_date, data_type='forecast')
        weather_df.to_csv('weather_data.csv')
        city, country = find_nearest_city_country(lat, lon)
        return px.line(weather_df), f'Weather at {city} in {country} for the next days  \n (location : lat : {lat:.3f}, lon {lon:.3f})'

    elif not(start_date is None) and not(end_date is None) and not(lat == '') and not(lon == ''):
        weather_df = get_weather_data((lat, lon), start_date, end_date=end_date, data_type='archive')
        weather_df.to_csv('weather_data.csv')
        city, country = find_nearest_city_country(lat, lon)
        return px.line(weather_df), f'Weather at {city} in {country} form {start_date} to {end_date}  \n (location : lat : {lat:.3f}, lon {lon:.3f})'
    else:
        return no_update, f'Please fill all the fields'


@app.callback(Output("lat-input", "value"),
              Output("lon-input", "value"),
              [Input("map", "data")],
              prevent_initial_call=True)
def fill_input(data):
    return data['lat'], data['lng']


@app.callback(Output("PV_graph", "figure"),
              Output("text_result", "children"),
              [Input("btn_PV_prod", "n_clicks")],
              [State("lat-input", "value"),
               State("lon-input", "value"),
               State("azimuth-input", "value"),
               State("tilt-input", "value"),
               State("power-input", "value")],
              prevent_initial_call=True)
def PV_calculation(n_clicks, lat, lon, azi, til, pow_):
    if n_clicks > 0:
        if azi == '':
            azi = 0
        if til == '':
            til = 0
        if pow_ == '':
            pow_ = 1
        azi = float(azi)
        til = float(til)
        pow_ = float(pow_)
        weather_df = pd.read_csv('weather_data.csv', parse_dates=['date'], index_col='date')
        power = estimate_pv_production(weather_df, lat, lon, pow_, til, azi)
        power.to_csv('power_data.csv')
        return px.line(power), print_result(power, lat)


@app.callback(
    Output("download_weather", "data"),
    Input("btn_dl_weather", "n_clicks"),
    prevent_initial_call=True
)
def download_csv_w(n_clicks):
    return dcc.send_file('weather_data.csv')


@app.callback(
    Output("download_power", "data"),
    Input("btn_dl_power", "n_clicks"),
    prevent_initial_call=True
)
def download_csv_p(n_clicks):
    return dcc.send_file('power_data.csv')


if __name__ == '__main__':
    app.run_server(debug=False)
