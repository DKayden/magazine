from modbus_client import Modbus_Client
from config import *
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread

import logging
import requests
import time
import json

amr_idle = True

data = {
    "floor1_truoc": -1,
    "floor1_sau": -1 ,
    "floor2_truoc": -1,
    "floor2_sau": -1,
}


app = Flask(__name__)
CORS(app=app)
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route("/conveyor", methods=["POST"])
def conveyor():
    content = request.json
    if (content['floor'] == 1) and (content['vt'] == 'truoc') and (content['type'] == 'unload') and (content['status'] == 'start'):
        client_modbus.writeRegister(FLOOR_1_FRONT, 1)
    elif (content['floor'] == 1) and (content['vt'] == 'truoc') and (content['type'] == 'unload')and (content['status'] == 'stop'):
        client_modbus.writeRegister(FLOOR_1_FRONT, 0)

    elif (content['floor'] == 2) and (content['vt'] == 'truoc') and (content['type'] == 'load') and (content['status'] == 'start'):
        client_modbus.writeRegister(FLOOR_1_FRONT, 1)
    elif (content['floor'] == 2) and (content['vt'] == 'truoc') and (content['type'] == 'load')and (content['status'] == 'stop'):
        client_modbus.writeRegister(FLOOR_1_FRONT, 0)
    
    elif (content['floor'] == 1) and (content['vt'] == 'sau') and (content['type'] == 'unload')and (content['status'] == 'start'):
        client_modbus.writeRegister(FLOOR_1_REAR, 1)
    elif (content['floor'] == 1) and (content['vt'] == 'sau') and (content['type'] == 'unload')and (content['status'] == 'stop'):
        client_modbus.writeRegister(FLOOR_1_REAR, 0)
    
    elif (content['floor'] == 2) and (content['vt'] == 'truoc') and (content['type'] == 'unload')and (content['status'] == 'start'):
        client_modbus.writeRegister(FLOOR_2_FRONT, 1)
    elif (content['floor'] == 2) and (content['vt'] == 'truoc') and (content['type'] == 'unload')and (content['status'] == 'stop'):
        client_modbus.writeRegister(FLOOR_2_FRONT, 0)
    
    elif (content['floor'] == 1) and (content['vt'] == 'truoc') and (content['type'] == 'load')and (content['status'] == 'start'):
        client_modbus.writeRegister(FLOOR_2_FRONT, 1)
    elif (content['floor'] == 1) and (content['vt'] == 'truoc') and (content['type'] == 'load')and (content['status'] == 'stop'):
        client_modbus.writeRegister(FLOOR_2_FRONT, 0)

    elif (content['floor'] == 2) and (content['vt'] == 'sau') and (content['type'] == 'unload')and (content['status'] == 'start'):
        client_modbus.writeRegister(FLOOR_2_REAR, 1)
    elif (content['floor'] == 2) and (content['vt'] == 'sau') and (content['type'] == 'unload')and (content['status'] == 'stop'):
        client_modbus.writeRegister(FLOOR_2_REAR, 0)

    if content['type'] == 'begin':
        client_modbus.writeRegister(10008, 1)
    elif content['type'] == 'end':
        client_modbus.writeRegister(10008, 0)
        
    return jsonify({'result':True,'desc':""})

@app.route("/signal", methods=["GET"])
def get_signal():
    return jsonify({
        'floor1_truoc': data["floor1_truoc"],
        'floor1_sau': data["floor1_sau"],
        'floor2_truoc': data["floor2_truoc"],
        'floor2_sau': data["floor2_sau"]
    }), 200

@app.route("/reset", methods=["POST"])
def reset():
    content = request.json
    if content['data'] == True:
        client_modbus.writeRegister(10000, 0)
        client_modbus.writeRegister(10001, 0)
        client_modbus.writeRegister(10002, 0)
        client_modbus.writeRegister(10003, 0)
    return jsonify({'content': 'okie'})

def poll_signal(line_call: Modbus_Client):
    while True:
        _signal = line_call.readHoldingReg(ADDRESS_SIGNAL, 4)[:4]
        data["floor2_truoc"] = _signal[0]
        data["floor2_sau"] = _signal[1]
        data["floor1_truoc"] = _signal[2]
        data["floor1_sau"] = _signal[3]

        print("DATA: ", data)
        time.sleep(0.5)

def send_mission(data: dict):
    try:
        resp = requests.post(url=URL_AMR_RUN, data=json.dumps(data), headers=HEADERS, timeout=10)
        while resp.status_code != 200:
            resp = requests.post(url=URL_AMR_RUN, data=json.dumps(data), headers=HEADERS, timeout=10)
            time.sleep(1)
    except requests.exceptions.HTTPError as errh:
        logging.error("Http Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        logging.error("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        logging.error("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        logging.error("OOps: Something Else",err)

def poll_mission():
    while True:
        if data["floor1_sau"] == 1:
            send_mission({
                'type': '',
                'mission': 'line',
                'vt': 'sau',
                'floor': 1,
                'method': 'auto'
            })
        elif data["floor1_truoc"] == 1:
            send_mission({
                'type': '',
                'mission': 'line',
                'vt': 'truoc',
                'floor': 1,
                'method': 'auto'
            })
        time.sleep(5)
        

def poll_amr_status():
    while True:
        try:
            global amr_idle
            data = (requests.get(url=URL_AMR_STATUS, headers=HEADERS, timeout=10).content).decode('utf-8')
            data_dict = json.loads(data)
            amr_idle = data_dict['data']['idle']
            time.sleep(1)
        except requests.exceptions.HTTPError as errh:
            logging.error("Http Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            logging.error("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            logging.error("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            logging.error("OOps: Something Else",err)


if __name__ == "__main__":
    client_modbus = Modbus_Client(HOST_MODBUS_TCP, PORT_MODBUS_TCP, "rtu")
    task_status = Thread(target=poll_amr_status,args=()).start()
    task_server = Thread(target=app.run,args=(host:="0.0.0.0",port:=5000)).start()
    task_signal = Thread(target=poll_signal, args=(client_modbus,)).start()
    task_mission = Thread(target=poll_mission, args=()).start()


    

    
    
