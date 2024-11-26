
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread
from datetime import datetime
from mongodb import MongoDB

app = Flask(__name__)
CORS(app=app)

mongodb = MongoDB()
mongodb.connect_monggo()

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
        print("db", mongodb.db_log)
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
    

flask_thread = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000})
flask_thread.start()