from pymongo import MongoClient
from datetime import datetime
import time
from uuid import uuid4

class MongoDB():
    def __init__(self):
        self.connect = False
        self.name_collection_log = f"sev_log_{datetime.now().month}"
        self.name_collection_history = f"sev_history_{datetime.now().month}"
        self.url = "mongodb://localhost:27017/"
        self.options = {
            "serverSelectionTimeoutMS": 2000,
            "socketTimeoutMS": 2000
        }
        self.mongo = MongoClient(self.url, **self.options)
        self.database = None
        self.db_log = None
        self.db_history = None
        self.arr_collection = []
        self.check_write_connect = False
    def connect_monggo(self):
        try:
            result = self.mongo.list_databases()
            if result:
                for collection in result:
                    self.arr_collection.append(collection["name"])
                self.database = self.mongo["sev"]
                self.db_log = self.database[self.name_collection_log]
                self.db_history = self.database[self.name_collection_history]
                self.connect = True
                self.db_log.insert_one({
                   "content": "connect db mongo thành công",
                    "point": "",
                    "desc": "",
                    "key": str(uuid4()),
                    "timestamp": datetime.now().timestamp(),
                    "date": datetime.today().strftime("%Y-%m-%d"),
                })
                self.check_write_connect = False
        except Exception as E :
            print("Reconnect Db ", E)
            if not self.check_write_connect:
                self.db_log.insert_one({
                    "content": "re-conenct db",
                    "point": "",
                    "desc": "",
                    "key": str(uuid4()),
                    "timestamp": datetime.now().timestamp(),
                    "date": datetime.today().strftime("%Y-%m-%d"),
                })
                self.check_write_connect = True
            time.sleep(2)
            self.connect_monggo()