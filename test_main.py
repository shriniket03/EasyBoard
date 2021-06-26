from main import app
from config import DevConfig, ProdConfig

import pytest
import json
import time

@pytest.fixture
def client():
    app.config.from_object(DevConfig)
    return app.test_client()

@pytest.mark.asyncio
async def test_haversine(client):
    """Test haversine calculation."""
    start = time.time()
    rv = await client.get('/api/distance', query_string={
            'destinLong':103.99218503125105,
            'destinLat':1.37089633004837, 
            'originLong':103.63848850236249,
            'originLat': 1.3302930303817977
    })
    body = await rv.get_data()
    assert rv.status_code == 200
    assert time.time() - start <= 0.1
    assert float(body) - 39.576757658125956 < 1e-3

@pytest.mark.asyncio
async def test_bus_stops_normal(client):
    """ Test bus stops API with a normal bus """
    start = time.time()
    rv = await client.get('/api/busStop', query_string={
            'currentBusStop' : '1.3347077916151044, 103.74772153964176', #IMM
            'busNumber' : '188',
            'destinBusStop' : '1.367550, 103.750183', ##bb driving
            'numStops' : '14'
    })
    data = json.loads(await rv.get_data())
    assert rv.status_code == 200
    assert time.time() - start <= 0.1
    assert data['busNames']== ['IMM Bldg','Blk 286A','Blk 288E','Blk 241','Blk 190','Blk 185','Blk 146','Opp Blk 127','Bef Bt Batok West Ave 5','Opp Blk 305','Opp Blk 315','Blk 419','Opp Blk 336','HomeTeamNS','Bt Batok Driving Ctr']
    assert data['busCodes'] == ['28659', '28649', '28639', '28621', '43691', '43379', '43329', '43409', '43469', '43479', '43489', '43499', '43839', '43649', '43521']

@pytest.mark.asyncio
async def test_bus_stops_loop(client):
    """ Test bus stops API with a loop bus """
    start = time.time()
    rv = await client.get('/api/busStop', query_string={
            'currentBusStop' : '1.361811,103.9551834',
            'busNumber' : '293',
            'destinBusStop' : '1.35407,103.94339',
            'numStops' : '5'
    })
    data = json.loads(await rv.get_data())
    assert rv.status_code == 200
    assert time.time() - start <= 0.1
    assert data['busNames'] == ['Dunman Sec Sch', 'Blk 484', 'Blk 430', 'Blk 418', 'BLK 503', 'Tampines Int']
    assert data['busCodes'] == ['76271', '76351', '76361', '76391', '76199', '75009']

@pytest.mark.asyncio
async def test_bus_stops_feeder(client):
    """ Test bus stops API with a feeder bus """
    start = time.time()
    rv = await client.get('/api/busStop', query_string={
            'currentBusStop' : '1.35407,103.9433',
            'busNumber' : '293',
            'destinBusStop' : '1.35649,103.9575483',
            'numStops' : '8'
    })
    data = json.loads(await rv.get_data())
    assert rv.status_code == 200
    assert time.time() - start <= 0.1
    assert data['busNames'] == ['Tampines Int', 'BLK 401', 'Blk 417', 'Blk 496F', 'Blk 493B', 'Blk 491C', 'Opp Blk 489A', 'Opp Blk 487B', 'Blk 390']
    assert data['busCodes'] == ['75009', '76191', '76399', '76369', '76359', '76279', '76269', '76259', '76239']

@pytest.mark.asyncio
async def test_bus_code(client):
    """ Test bus code API """
    start = time.time()
    rv = await client.get('/api/busCode', query_string={
            'originBusStop' : 'Opp IMM Bldg',
            'busNumber' : '188'
    })
    data = json.loads(await rv.get_data())
    assert rv.status_code == 200
    assert time.time() - start <= 0.1
    assert data == 28651

def test_api_key():
    app.config.from_object(DevConfig)
    assert app.config.get('GOOGLE_API_KEY') == 'xxx'

def test_prod_api_key():
    app.config.from_object(ProdConfig)
    assert app.config.get('GOOGLE_API_KEY')
