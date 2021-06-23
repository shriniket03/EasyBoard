import math
import os
import pickle

import flask
from flask import request, jsonify
from math import cos, asin, sqrt, radians, sin
import requests
import pandas as pd
from sklearn.neighbors import KDTree
import numpy as np
import itertools
import simplejson
from fasthaversine import haversine

app = flask.Flask(__name__)
app.config["DEBUG"] = True
stops_df = pd.read_pickle('stops')
routes_df = pd.read_pickle('routes')
tree=pickle.load(open('pickle','rb'))
# Retrieve GOOGLE_API_KEY from environment variable
# Compatible with most secrets management
app.config["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY")
if not app.config["GOOGLE_API_KEY"]:
    raise ValueError("No GOOGLE_API_KEY set for Flask application")

def get_nearest_bus_stop(lat, lon):
    _, nearest_ind = tree.query([[lat,lon]], k=1)
    return stops_df.iloc[nearest_ind[0][0]]

@app.route('/api/distance', methods=['GET'])
def getDistance():
    if all(x in request.args for x in ['destinLong', 'destinLat','originLong','originLat']):
        origin = (float(request.args['originLat']), float(request.args['originLong']))
        destin = (float(request.args['destinLat']), float(request.args['destinLong']))
    else:
        return "Error: Parameters not properly provided. Please specify properly."

    return str(haversine([origin], [destin], unit='km'))


@app.route('/api/routing', methods=['GET'])
def getRoute():
    try:
        if all(x in request.args for x in ['destinLong', 'destinLat','originLong','originLat']):
            origin = (float(request.args['originLat']), float(request.args['originLong']))
            destin = (float(request.args['destinLat']), float(request.args['destinLong']))
        else:
            return "Error: Proper parameters not provided"
    except ValueError:
        return "Error: Proper parameters not provided"

    string = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        'origin': f'{origin[0]},{origin[1]}',
        'destination': f'{destin[0]},{destin[1]}',
        'key': app.config["GOOGLE_API_KEY"] ,
        'avoid': 'indoor',
        'units': 'km',
        'transit_mode': 'bus',
        'transit_routing_preference': 'less_walking',
        'mode': 'transit',
        'departure_time': 'now',
        'alternatives': 'true'
    }
    response = requests.get(string,params=params).json()
    instructions = []
    count = 0
    dictl = dict()
    for route in response['routes']:
        count += 1
        time = response['routes'][count - 1]['legs'][0]['duration']['text']
        itinerary = response['routes'][count - 1]['legs'][0]['steps']
        transfers = len(itinerary) - 1
        instructions = [time, transfers]
        for leg in itinerary:
            if leg['travel_mode'] == "WALKING":
                origin = (leg['start_location']['lat'], leg['start_location']['lng'])
                destination = (leg['end_location']['lat'], leg['end_location']['lng'])
                duration = leg['distance']['text']
                distance = leg['duration']['text']
                legSpecific = ("WALK", origin, destination, distance, duration)
                instructions.append(legSpecific)
            elif leg['travel_mode'] == "TRANSIT":
                departure = leg['transit_details']['departure_stop']['name']
                arrival = leg['transit_details']['arrival_stop']['name']
                busNumber = leg['transit_details']['line']['name']
                numStops = leg['transit_details']['num_stops']
                duration = leg['distance']['text']
                distance = leg['duration']['text']
                legSpecific = ("BUS", departure, arrival, busNumber, numStops, distance, duration)
                instructions.append(legSpecific)
            dictl[f"instructions{count}"] = instructions

    return simplejson.dumps(dictl)


@app.route('/api/busStop', methods=['GET'])
def busStops():
    currentBusStop = str(request.args['currentBusStop']).split(",")
    destinBusStop = str(request.args['destinBusStop']).split(",")
    busNumber = str(request.args['busNumber'])
    numberOfStops = int(request.args['numStops'])
    filtered_routes = routes_df[routes_df['ServiceNo'] == str(busNumber)]
    start_bus_stop = get_nearest_bus_stop(*currentBusStop)
    idx1 = np.where(filtered_routes['BusStopCode'] == start_bus_stop['BusStopCode'])[0][0]
    end_bus_stop = get_nearest_bus_stop(*destinBusStop)
    idx2 = np.where(filtered_routes['BusStopCode'] == end_bus_stop['BusStopCode'])[0][0]
    lister = pd.merge(stops_df, filtered_routes.iloc[idx1:idx2 + 1], on='BusStopCode').sort_values(by=['StopSequence'])['Description'].tolist()
    if len(lister)>numberOfStops:
        if lister.count(lister[0])>1:
            lister = lister[-numberOfStops-1:]
    output = {'instructions': lister}
    return simplejson.dumps(output)


@app.route('/api/busCode', methods=['GET'])
def getBusCode():
    if 'originBusStop' in request.args and 'busNumber' in request.args:
        originBusStop = str(request.args['originBusStop'])
        busNumber = str(request.args['busNumber'])
    else:
        return "Error: Proper parameters not provided"
    filtered_routes = routes_df[routes_df['ServiceNo'] == str(busNumber)]
    filtered_stops = stops_df[stops_df['Description'] == originBusStop]
    busStopCode = pd.merge(filtered_stops, filtered_routes, on='BusStopCode')['BusStopCode'].tolist()[0]
    return busStopCode

