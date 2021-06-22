import math

import flask
from flask import request, jsonify
from math import cos, asin, sqrt, radians, sin
import requests
import simplejson
from bs4 import BeautifulSoup
import itertools

app = flask.Flask(__name__)
app.config["DEBUG"] = True


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
                                                                      1]) + "&key=&avoid=indoor&units=km&transit_mode=bus&transit_routing_preference=less_walking&mode=transit&departure_time=now&alternatives=true"
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
    if 'currentBusStop' and 'busNumber' and 'destinBusStop' and 'numStops' in request.args:
        currentBusStop = str(request.args['currentBusStop'])
        destinBusStop = str(request.args['destinBusStop'])
        busNumber = str(request.args['busNumber'])
        numStops = str(request.args['numStops'])
    else:
        return "Error: Proper parameters not provided"

    data = requests.get('https://www.transitlink.com.sg/eservice/eguide/service_route.php?service=' + busNumber)
    soup = BeautifulSoup(data.content, 'html.parser')
    element = list(soup.find_all('td', class_='route', width=True))
    busStop = []
    for i in range(1, len(element)):
        temp = element[i].getText()
        temp = temp.lstrip('\xa0•\xa0')
        if temp != "Express":
            busStop.append(temp)
    try:
        split = busStop.index('Road / Bus Stop Description')
        dir1, dir2 = busStop[:split], busStop[split:]
        dir2.remove(dir2[0])
    except:
        dir1 = busStop
        dir2 = []
    usage = 0
    indices1 = [index for index, element in enumerate(dir1) if element == currentBusStop
                or element + " Int" == currentBusStop
                or element.split(" - ")[0].strip() == currentBusStop
                or element.replace("W'lands", "Woodlands") == currentBusStop]
    indices2 = [index for index, element in enumerate(dir1) if element == destinBusStop
                or element + " Int" == destinBusStop
                or element.split(" - ")[0].strip() == destinBusStop
                or element.replace("W'lands", "Woodlands") == destinBusStop]
    if len(indices1) == 0 and len(indices2) == 0:
        indices1 = [index for index, element in enumerate(dir2) if element == currentBusStop
                    or element + " Int" == currentBusStop
                    or element.split(" - ")[0].strip() == currentBusStop
                    or element.replace("W'lands", "Woodlands") == currentBusStop]
        indices2 = [index for index, element in enumerate(dir2) if element == destinBusStop
                    or element + " Int" == destinBusStop
                    or element.split(" - ")[0].strip() == destinBusStop
                    or element.replace("W'lands", "Woodlands") == destinBusStop]
        usage = 1
    if len(indices1) == 0 and len(indices2) == 0:
        counter = 0
        for stuffedprata in dir1:
            stuffedprata.replace(" ", "+")
            a = requests.get("https://www.google.com/search?q=" + stuffedprata + "+bus+stop")
            soup = BeautifulSoup(a.content, 'html.parser')
            element = list(soup.find_all('span'))
            if element[15].getText() == currentBusStop:
                indices1.append(counter)
                usage=0
                break
            counter += 1
    if len(indices1) == 0 and len(indices2) == 0:
        counter = 0
        for stuffedprata in dir2:
            stuffedprata.replace(" ", "+")
            a = requests.get("https://www.google.com/search?q=" + stuffedprata + "+bus+stop")
            soup = BeautifulSoup(a.content, 'html.parser')
            element = list(soup.find_all('span'))
            if element[15].getText() == currentBusStop:
                indices1.append(counter)
                usage=1
                break
            counter += 1
    if len(indices2) == 1 and len(indices1) == 0:
        indices1.append((indices2[0] - int(numStops)))
    if len(indices1) == 1 and len(indices2) == 0:
        indices2.append((indices1[0] + int(numStops)))
    if len(indices2) != 0 and len(indices1) == 0:
        for integer in indices2:
            indices1.append(integer - int(numStops))
        for thing in list(indices1):
            if usage == 0:
                if googleName(dir1[thing]) == currentBusStop:
                    indices1 = list().append(thing)
                    break
            if usage == 1:
                if googleName(dir2[thing]) == currentBusStop:
                    indices1 = list().append(thing)
                    break
    if len(indices1) != 0 and len(indices2) == 0:
        for integer in indices1:
            indices2.append(integer + int(numStops))
        for thing in list(indices2):
            if usage == 0:
                if googleName(dir1[thing]) == destinBusStop:
                    indices2 = list().append(thing)
                    break
            if usage == 1:
                if googleName(dir2[thing]) == destinBusStop:
                    indices2 = list().append(thing)
                    break
    possible = list(itertools.product(indices1, indices2))
    final = ()
    for element in possible:
        if (element[1] - element[0]) != int(numStops):
            continue
        final = element
    finalList = []
    if usage == 0:
        for stop in range(final[0], final[1] + 1):
            finalList.append(dir1[stop])
    if usage == 1:
        for stop in range(final[0], final[1] + 1):
            finalList.append(dir2[stop])

    output = {'instructions': finalList}

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


def googleName(normalName):
    normalName = normalName.replace(" ", "%20")
    string = "https://maps.googleapis.com/maps/api/geocode/json?key=&address=" + normalName
    response = requests.get(string)
    response = response.json()
    name = response["results"][0]["address_components"][0]["long_name"]
    return name
