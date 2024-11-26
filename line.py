import logging
import requests
import json
import time

class Line():
    def __init__(self, host, port) -> None:
        self.host = host
        self.port = port
        self.heders = {'content-type': 'application/json'}
        self.timeout = 10
        self.url = self.host + ":" + str(self.port)
        
    def listen(self):
        try:
            res = requests.get(url=self.url + "/signal", headers=self.heders, timeout=self.timeout)
            res.raise_for_status()
            data = res.content.decode('utf-8')
            return data
        except requests.exceptions.HTTPError as errh:
            logging.error("Http Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            logging.error("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            logging.error("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            logging.error("OOps: Something Else",err)
        return ""
    
    def send(self, floor: int=0, vt: str='', type: str='', status :str=''):
        try:
            data = {
                "floor": floor,
                "vt": vt,
                "type": type,
                "status": status
            }
            resp = requests.post(url=self.url +"/conveyor", data=json.dumps(data), headers=self.heders, timeout=self.timeout)
            while resp.status_code != 200:
                resp = requests.post(url=self.url +"/conveyor", data=json.dumps(data), headers=self.heders, timeout=self.timeout)
                time.sleep(1)
        except requests.exceptions.HTTPError as errh:
            logging.error("Http Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            logging.error("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            logging.error("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            logging.error("OOps: Something Else",err)
