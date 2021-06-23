import math
import os
import pickle

import flask
from flask import request, jsonify
from math import cos, asin, sqrt, radians, sin
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sklearn.neighbors import KDTree
import numpy as np
import itertools
import simplejson

app = flask.Flask(__name__)
app.config["DEBUG"] = True
stops_df = pd.read_pickle('stops')
routes_df = pd.read_pickle('routes')
tree=pickle.load(open('pickle','rb'))
app.config['GOOGLE_API_KEY'] = 'AIzaSyBv2C67gbDICww4maZLs0vxqkO6XdJ_PlE'
# Retrieve GOOGLE_API_KEY from environment variable
# Compatible with most secrets management
#app.config["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY")
#if not app.config["GOOGLE_API_KEY"]:
    #raise ValueError("No GOOGLE_API_KEY set for Flask application")

def get_nearest_bus_stop(lat, lon):
    _, nearest_ind = tree.query([[lat,lon]], k=1)
    return stops_df.iloc[nearest_ind[0][0]]

@app.route('/api/distance', methods=['GET'])
def getDistance():
    if 'originLat' and 'originLong' and 'destinLat' and 'destinLong' in request.args:
        origin = (float(request.args['originLat']), float(request.args['originLong']))
        destin = (float(request.args['destinLat']), float(request.args['destinLong']))
    else:
        return "Error: Parameters not properly provided. Please specify properly."
    lon1, lat1, lon2, lat2 = map(radians, [origin[1], origin[0], destin[1], destin[0]])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles

    return jsonify(c * r)


@app.route('/api/routing', methods=['GET'])
def getRoute():
    try:
        if 'originLat' and 'originLong' and 'destinLat' and 'destinLong' in request.args:
            origin = (float(request.args['originLat']), float(request.args['originLong']))
            destin = (float(request.args['destinLat']), float(request.args['destinLong']))
        else:
            return "Error: Proper parameters not provided"
    except ValueError:
        return "Error: Proper parameters not provided"

    string = "https://maps.googleapis.com/maps/api/directions/json?origin=" + str(origin[0]) + "," + str(
        origin[1]) + "&destination=" + str(destin[0]) + "," + str(destin[
                                                                      1]) + "&key=" + app.config['GOOGLE_API_KEY'] + "&avoid=indoor&units=km&transit_mode=bus&transit_routing_preference=less_walking&mode=transit&departure_time=now&alternatives=true"
    response = requests.get(string)
    response = response.json()
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
    if 'originBusStop' and 'busNumber' in request.args:
        originBusStop = str(request.args['originBusStop'])
        busNumber = str(request.args['busNumber'])
    else:
        return "Error: Proper parameters not provided"
    try:
        data = requests.get('https://www.transitlink.com.sg/eservice/eguide/service_route.php?service=' + busNumber)
        soup = BeautifulSoup(data.content, 'html.parser')
        element = list(soup.find_all('td'))
        stuff = []
        for item in element:
            if item.getText() == '\xa0':
                continue
            stuff.append(item.getText())
        inde = stuff.index('0.0')
    except IndexError:
        busNumber = busNumber[:-1]
        data = requests.get('https://www.transitlink.com.sg/eservice/eguide/service_route.php?service=' + busNumber)
        soup = BeautifulSoup(data.content, 'html.parser')
        element = list(soup.find_all('td'))
        stuff = []
        for item in element:
            if item.getText() == '\xa0':
                continue
            stuff.append(item.getText())
        inde = stuff.index('0.0')
    stuff = stuff[inde:-2]
    temp = []
    for thing in stuff:
        if originBusStop == thing[3:]:
            temp = stuff[stuff.index(thing) - 1]
            temp = temp.strip()
            break
        else:
            continue
    return temp

app.run()