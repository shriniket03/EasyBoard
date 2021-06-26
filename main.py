import os
import pickle
from quart import Quart,request
import requests
import pandas as pd
import numpy as np
import simplejson
from haversine import haversine

stops_df = pd.read_pickle('resources/stops')
routes_df = pd.read_pickle('resources/routes')
tree=pickle.load(open('resources/pickle','rb'))

app = Quart(__name__)

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

    return str(haversine(origin, destin))


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
                departure = str(leg['transit_details']['departure_stop']['location']['lat']) + "," + str(leg['transit_details']['departure_stop']['location']['lng'])
                arrival = str(leg['transit_details']['arrival_stop']['location']['lat']) + "," + str(leg['transit_details']['arrival_stop']['location']['lng'])
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
    filtered_routes = routes_df[routes_df['ServiceNo']==str(busNumber)] #291T support
    idx2 = np.where(filtered_routes['BusStopCode'] == get_nearest_bus_stop(*destinBusStop)['BusStopCode'])[0]
    idx1 = np.where(filtered_routes['BusStopCode'] == get_nearest_bus_stop(*currentBusStop)['BusStopCode'])[0]
    if len(idx1) > 1 or len(idx2) > 1:
        for st in idx1:
            for en in idx2:
                if st + numberOfStops == en:
                    break
            else:
                continue
            break
        idx1 = st
        idx2 = en
    else:
        idx1 = idx1[0]
        idx2 = idx2[0]
    merged_df = pd.merge(stops_df, filtered_routes.iloc[idx1:idx2+1], on='BusStopCode')
    lister = merged_df.sort_values('StopSequence')['Description'].to_list()
    lister2 = merged_df.sort_values('StopSequence')['BusStopCode'].to_list()
    return simplejson.dumps({'busNames': lister,'busCodes':lister2})


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

if __name__ == '__main__':
    app.config.from_object('config.ProdConfig')
    app.run()