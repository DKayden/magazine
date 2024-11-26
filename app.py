from flask import Flask, request, jsonify
from flask_cors import CORS
from config import *
from magazine import Magazine
from validate import is_number
from mongodb import MongoDB
import time

import logging

app = Flask(__name__)
CORS(app=app)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


magazine = Magazine()

mongodb = MongoDB()
mongodb.connect_monggo()

@app.route("/relocation",methods=["POST"])
def relocation():
    content = request.json
    result = magazine.robot.relocation(data_possition=content['data'])
    magazine.robot.mesenger = "Thực Hiện Lấy lại Vị Trí Cho AMR"
    return jsonify({'result':True,'desc':result})

@app.route("/confirm", methods=['POST'])
def confirm_local():
    result = magazine.robot.confirm_local()
    magazine.robot.mesenger = "Xác Nhận Vị Trí Cho AMR"
    return jsonify({'result':True,'desc':result})

@app.route("/setDO",methods=['POST'])
def setDO():
    content = request.json
    result = magazine.robot.setDO(content)
    return jsonify({'result':True,'desc':result})

@app.route("/navigation", methods=["POST"])
def navigation():
    content = request.json
    result = magazine.robot.navigation(content)
    return jsonify({'result':True,'desc':result})
    
@app.route("/mode", methods=["POST"])
def mode_api():
    content = request.json
    magazine.robot.mode = content['mode']
    if magazine.robot.mode == 'manual':
        magazine.robot.line_auto_web = ['line25','line27','line40', 'line41']
        magazine.robot.mesenger = "Chuyển Chế Độ Sang Manual"
    elif magazine.robot.mode == 'auto':
        magazine.robot.line_auto_web = ["line40_truoc", "line41_truoc"]
        magazine.robot.mesenger = "Chuyển Chế Độ Sang Auto"
    return jsonify({'result':True,'desc':content})

@app.route("/status",methods=["GET"])
def getFileBlock():
    return jsonify({'data':magazine.robot.data_Status}),200

@app.route("/monitor",methods=["POST"])
def monitor_amr():
    content = request.json
    if magazine.robot.mode == 'manual':
        magazine.robot.monitor(content)
        return jsonify({'result':True}),200
    else:
        return jsonify({'message': "khong chay"}), 401
    
@app.route("/conveyor", methods=["POST"])
def conveyor():
    content = request.json
    if content['type'] == 'stop':
        magazine.server_modbus.datablock_input_register.setValues(address=0x05,values=[magazine.dir.stop])
        magazine.robot.mesenger = "Dừng Băng Tải"
    elif content['type'] == 'cw':
        magazine.server_modbus.datablock_input_register.setValues(address=0x05,values=[magazine.dir.cw_out])
        magazine.robot.mesenger = "Quay Băng Tải"
    elif content['type'] == 'ccw':
        magazine.server_modbus.datablock_input_register.setValues(address=0x05,values=[magazine.dir.ccw_out])
        magazine.robot.mesenger = "Quay Băng Tải"
    else:
        pass
    return jsonify({'result':True,'desc':""})

@app.route("/stopper", methods=["POST"])
def stopper():
    content = request.json
    if content['status']:
        magazine.server_modbus.datablock_input_register.setValues(address=0x04,values=[magazine.stopper.All_On])
        magazine.robot.mesenger = "Mở Tất Cả Stopper"
    else:
        magazine.server_modbus.datablock_input_register.setValues(address=0x04,values=[magazine.stopper.All_Off])
        magazine.robot.mesenger = "Đóng Tất Cả Stopper"
    return jsonify({'result':True,'desc':content['status']})

@app.route("/type", methods=["POST"])
def api_type_():  
    content = request.json
    content_result=content["type"]
    if content_result == 'cancel':
        magazine.robot.idle = True
        magazine.error = False
        magazine.robot.cancel = True
        magazine.server_modbus.datablock_input_register.setValues(address=0x05,values=[magazine.dir.stop])
        magazine.robot.mesenger = "Ấn Nút Hủy Trên Màn Hình"
        magazine.magazine_status = {
            'type' : '',
            'mission' : '',
            'vt': '',
            'floor': 0,
            'busy' : 0
        }
        magazine.Call = {
            'Call_Unload_L40' : -1,
            'Call_Load_L40' : -1,

            'Call_Unload_L41' : -1,
            'Call_Load_L41' : -1,

            'Call_Unload_L25' : -1,
            'Call_Load_L25' : -1,

            'Call_Unload_L27' : -1,
            'Call_Load_L27' : -1
        }
        magazine.robot.nav_cancel()
    elif (content['type'] == 'pause'):
        magazine.robot.nav_pause()
        magazine.robot.mesenger = "Ấn Nút Dừng Trên Màn Hình"
    elif (content['type'] == 'resume'):
        magazine.robot.nav_resume()
        magazine.robot.mesenger = "Ấn Nút Tiếp Tục Trên Màn Hình"
    else:
        pass
    return jsonify({'result':True,'desc':''})

@app.route("/line_auto",methods=["POST"])
def api_select_line_auto_mode():
    content = request.json
    lines = content['line']
    magazine.robot.line_auto_web=[]
    for line in lines:
        if line == "line25":
            magazine.robot.line_auto_web.append("line25_truoc")
            magazine.robot.line_auto_web.append("line25")
        if line == "line27":
            magazine.robot.line_auto_web.append("line27_truoc")
            magazine.robot.line_auto_web.append("line27")
        if line == "line40_truoc":
            magazine.robot.line_auto_web.append("line40_truoc")
        if line == "line40_sau":
            magazine.robot.line_auto_web.append("line40_sau")
        if line == "line41_truoc":
            magazine.robot.line_auto_web.append("line41_truoc")
        if line == "line41_sau":
            magazine.robot.line_auto_web.append("line41_sau")

    logging.info(magazine.robot.line_auto_web)
    return jsonify({'result':True,'desc':''})

@app.route("/run", methods=["POST"])
def run_api():
    content = request.json
    if ((magazine.robot.mode == 'manual') and (content['method'] == "manual")) or ((magazine.robot.mode == 'auto') and (content['method'] == "auto")):
        magazine.magazine_status = {
            'type' : content['type'],
            'mission' : content['line'],
            'vt': content['vt'],
            'floor': content['floor'],
            'busy' : 1
        }
    return jsonify({'message': 'Success'}), 200

@app.route("/lift", methods=["POST"])
def lift():
        content = request.json
        if is_number(content['height']) and 0 <= content['height'] <= 850:
            magazine.server_modbus.datablock_input_register.setValues(address=0x03,values=[content['height']])
            magazine.robot.mesenger = "Thang Di Chuyển Với Độ Cao" + str(content['height'])
            return jsonify({'result':True,'desc':str(content['height'])})
        else:
            return jsonify({'result':False,'desc':"Phải gửi chiều cao là số nguyên và 0 <= height <= 850"})

@app.route("/log",methods=["POST"])
def post_log():
    content = request.json
    if content:
        try:
            mongodb.db_log.insert_one(content)
            return jsonify({"result": True}), 200
        except:
            return jsonify({}), 500
    return jsonify({}), 400
            
@app.route("/log",methods=["GET"])
def get_log():
    try:
        date = request.args.getlist("date")
        arr = []
        result = mongodb.db_log.find({"date": date[0]}) if len(date) else mongodb.db_log.find()
        for item in result:
            item['_id'] = str(item['_id'])
            arr.append(item)
        return jsonify(arr), 200
    except:
        return jsonify({}), 500
    
@app.route("/history",methods=["POST"])
def post_history():
    content = request.json
    if content:
        try:
            mongodb.db_history.insert_one(content)
            return jsonify({"result": True}), 200
        except:
            return jsonify({}), 500
    return jsonify({}), 400

@app.route("/history",methods=["GET"])
def get_history():
    try:
        date = request.args.getlist("date")
        arr = []
        result = mongodb.db_history.find({"date": date[0]}) if len(date) else mongodb.db_history.find()
        for item in result:
            item['_id'] = str(item['_id'])
            arr.append(item)
        return jsonify(arr), 200
    except:
        return jsonify({}), 500