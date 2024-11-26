from line import Line
from uuid import uuid4
from config import *
from modbus_server import ModbusServer
from control import ESA_API, Stopper, Dir, Color
from validate import TypeMagazineError, LineNameMagazineError

import time
import logging
import requests
import json

AREA1 = ['line25', 'line27', 'line25_truoc', 'line27_truoc', '2', '3','4','5']
AREA2 = ['line40', 'line41', 'line40_truoc', 'line41_truoc', 'line40_sau', 'line41_sau', '6', '7']
LINE_TRUOC = ['line25_truoc', 'line27_truoc', 'line40_truoc', 'line41_truoc', 'line25', 'line27', 'line40', 'line41']
LINE_SAU = ['line40_sau', 'line41_sau']

def info_line(line:str):
    try:
        url =f'http://localhost:5600/{line}'
        headers={'content-type': 'application/json'}
        data = (requests.get(url=url,data={}, headers=headers,timeout=3).content).decode('utf-8')
        return data
    except requests.exceptions.ConnectionError as conner:
        logging.warning(str(conner))
    except requests.exceptions.ReadTimeout as timer:
        logging.warning(str(timer))
    except Exception as E:
        logging.warning(str(E))

class Magazine():
    def __init__(self) -> None:

        self.server_modbus = ModbusServer()
        self.robot = ESA_API('192.168.192.5')
        self.stopper = Stopper()
        self.dir = Dir()
        self.color = Color()
        self.check_sensor_conveyor = False
        self.Call = {
            'Call_Unload_L40' : -1,
            'Call_Load_L40' : -1,

            'Call_Unload_L41' : -1,
            'Call_Load_L41' : -1,

            'Call_Unload_L25' : -1,
            'Call_Load_L25' : -1,

            'Call_Unload_L27' : -1,
            'Call_Load_L27' : -1
        }

        
        self.magazine_status = {
            'type' : '',
            'mission' : '',
            'vt': '',
            'floor': 0,
            'busy' : 0
        }

        self.magazine_mission = {
            'id': '',
            'line': '',
            'type': '',
            'vt': '',
            'floor': 0,
            'height': 0
        }

        self.magazine_info = {
            'mission': '',
            'floor': 0
        }

        self.check_mission = True
        self.error = False
        self.call_mission = True
        self.history = {
            'mission': '',
            'floor': 0,
            'type': '',
            'status': ''
        }

    def tranfer_magazine(self, floor:int, vt: str, stopper: int, conveyor: int, type: str,
                        line_unloader: Line, line_loader: Line) -> None:
        self.server_modbus.datablock_input_register.setValues(address=0x04,values=[stopper]) #Bật stopper
        while self.server_modbus.datablock_holding_register.getValues(address=0x03,count=1)!=[stopper]:
            logging.info(self.server_modbus.datablock_holding_register.getValues(address=0x03,count=1))
            time.sleep(1)
        if type == "unload":
            line_unloader.send(floor=floor, vt=vt, type=type, status='start')
        else:
            line_loader.send(floor=floor, vt=vt, type=type, status='start')
        self.server_modbus.datablock_input_register.setValues(address=0x05,values=conveyor)
        if (type == 'unload' and floor == 1) or (type == 'load' and floor == 2):
            start_time = time.time()
            while self.server_modbus.datablock_holding_register.getValues(address=0x04,count=1)[0] != conveyor:
                logging.info(self.server_modbus.datablock_holding_register.getValues(address=0x04,count=1))
                time.sleep(1)
                if (time.time() - start_time) > 20:
                    
                    self.error = True
                    self.robot.mesenger = "Ấn Nút Hủy Trên Màn Hình De RESET AMR"
                    self.history['status'] = 'ERROR'
                    if type == "unload":
                        line_unloader.send(floor=floor, vt=vt, type=type, status='stop')
                        line_unloader.send(type='end')
                    else:
                        line_loader.send(floor=floor, vt=vt, type=type, status='stop')
                        line_loader.send(type='end')
                    self.server_modbus.datablock_input_register.setValues(address=0x05,values=self.dir.stop)
                if self.robot.cancel:
                    
                    self.server_modbus.datablock_input_register.setValues(address=0x04,values=[self.stopper.All_Off])
                    self.server_modbus.datablock_input_register.setValues(address=0x03,values=[100])
                    self.robot.navigation({'id':STANDBY})
                    return
            
        elif (type == 'unload' and floor == 2) or (type == 'load' and floor == 1):
            if type == 'load':
                start_time = time.time()
                while True:
                    data_signal = line_loader.listen()
                    data_dict_signal = json.loads(data_signal)
                    if data_dict_signal['floor2_truoc']  == 0:
                        break
                    if (time.time() - start_time) > 20:
                        self.error = True

                        self.robot.mesenger = "Ấn Nút Hủy Trên Màn Hình De RESET AMR"
                        self.history['status'] = 'ERROR'
                        if type == "unload":
                            line_unloader.send(floor=floor, vt=vt, type=type, status='stop')
                            line_unloader.send(type='end')
                        else:
                            line_loader.send(floor=floor, vt=vt, type=type, status='stop')
                            line_loader.send(type='end')
                        self.server_modbus.datablock_input_register.setValues(address=0x05,values=self.dir.stop)
                    if self.robot.cancel:
                        self.server_modbus.datablock_input_register.setValues(address=0x04,values=[self.stopper.All_Off])
                        self.server_modbus.datablock_input_register.setValues(address=0x03,values=[100])
                        self.robot.navigation({'id':STANDBY})
                        return
            elif type == 'unload':
                if vt == 'truoc':
                    start_time = time.time()
                    while True:
                        data_signal = line_unloader.listen()
                        data_dict_signal = json.loads(data_signal)
                        if data_dict_signal['floor2_truoc']  == 0:
                            break
                        if (time.time() - start_time) > 20:
                            self.error = True
                            self.robot.mesenger = "Ấn Nút Hủy Trên Màn Hình De RESET AMR"
                            self.history['status'] = 'ERROR'
                            if type == "unload":
                                line_unloader.send(floor=floor, vt=vt, type=type, status='stop')
                                line_unloader.send(type='end')
                            else:
                                line_loader.send(floor=floor, vt=vt, type=type, status='stop')
                                line_loader.send(type='end')
                            self.server_modbus.datablock_input_register.setValues(address=0x05,values=self.dir.stop)
                        if self.robot.cancel:
                            self.server_modbus.datablock_input_register.setValues(address=0x04,values=[self.stopper.All_Off])
                            self.server_modbus.datablock_input_register.setValues(address=0x03,values=[100])
                            self.robot.navigation({'id':STANDBY})
                            return    
                else:
                    start_time = time.time()
                    while True:
                        data_signal = line_unloader.listen()
                        data_dict_signal = json.loads(data_signal)
                        if data_dict_signal['floor2_sau']  == 0:
                            break
                        if (time.time() - start_time) > 20:
                            self.error = True
                            self.robot.mesenger = "Ấn Nút Hủy Trên Màn Hình De RESET AMR"
                            self.history['status'] = 'ERROR'
                            if type == "unload":
                                line_unloader.send(floor=floor, vt=vt, type=type, status='stop')
                                line_unloader.send(type='end')
                            else:
                                line_loader.send(floor=floor, vt=vt, type=type, status='stop')
                                line_loader.send(type='end')
                            self.server_modbus.datablock_input_register.setValues(address=0x05,values=self.dir.stop)
                        if self.robot.cancel:
                            self.server_modbus.datablock_input_register.setValues(address=0x04,values=[self.stopper.All_Off])
                            self.server_modbus.datablock_input_register.setValues(address=0x03,values=[100])
                            self.robot.navigation({'id':STANDBY})
                            return
        self.history['status'] = 'SUCCESS'
        if type == "unload":
            line_unloader.send(floor=floor, vt=vt, type=type, status='stop')
        else:
            line_loader.send(floor=floor, vt=vt, type=type, status='stop')

    def run(self, task_magazine: dict, line_unloader: Line, line_loader: Line):
        #print("RUN")
        self.check_mission = True
        self.robot.idle = False
        self.robot.cancel = False
        
        self.robot.mesenger = "AMR NHẬN NHIỆM VỤ LINE " + str(task_magazine['line'])
        time.sleep(.5)
        self.robot.navigation(({
            'id': task_magazine['id'],
            'task_id':str(uuid4()),
            'source_id': "SELF_POSITION"
        }))

        self.robot.mesenger = "AMR đang di chuyển đến " + str(task_magazine['type']) + 'er Magazine ' + str(task_magazine['line'])
        while (self.robot.check_target(self.robot.data_Status, task_magazine['id']) == False):
            if self.robot.cancel:
                if self.magazine_mission['line'] in AREA1:
                    self.robot.navigation({'id':"LM101"})
                    self.robot.mesenger = "AMR Di Chuyển Chờ Nhiệm Vụ"
                else:
                    self.robot.navigation({'id':STANDBY})
                    self.robot.mesenger = "AMR Di Chuyển Chờ Nhiệm Vụ"
                return

        self.robot.mesenger = 'XE ĐÃ ĐẾN VỊ TRÍ THỰC HIỆN NHIỆM VỤ'
            
        if (task_magazine['type'] == 'load') and (task_magazine['floor'] == 2):
            data = line_loader.listen()
            if data:
                try:
                    data_dict = json.loads(data)
                    if data_dict['floor1_truoc']  == 0:
                        self.robot.mesenger = "Magazine Đã Được Nhân Viên Trong Nhà Máy Lấy. AMR Di Chuyển Chờ Nhiệm Vụ"
                        self.check_mission = False
                        if self.magazine_mission['line'] in AREA1:
                            self.robot.navigation({'id':"LM101"})
                        else:
                            self.robot.navigation({'id':STANDBY})
                            return
                except json.JSONDecodeError as e:
                    self.check_mission = False
                    self.robot.mesenger = "Lỗi JsonDecoder: " + str(e)
                    logging.error("Lỗi JsonDecoder ", e)
                    return    
            else:
                self.check_mission = False
                self.robot.mesenger = f"Line {task_magazine['line']} mất kết nối với AMR. Xe di chuyển về vị trí chờ"
                
                return
            
        if (task_magazine['type'] == 'unload') and (task_magazine['floor'] == 1) and (task_magazine['vt'] == 'truoc'):
            data = line_unloader.listen()
            if data:
                try:
                    data_dict = json.loads(data)
                    if data_dict['floor1_truoc']  == 0:
                        self.check_mission = False
                        self.robot.mesenger = "Magazine Đã Được Nhân Viên Trong Nhà Máy Lấy. AMR Di Chuyển Chờ Nhiệm Vụ"
                        if self.magazine_mission['line'] in AREA1:
                            self.robot.navigation({'id':"LM101"})
                        else:
                            self.robot.navigation({'id':STANDBY})
                            return
                except json.JSONDecodeError as e:
                    self.check_mission = False
                    self.robot.mesenger = "Lỗi JsonDecoder: " + str(e)
                    logging.error("Lỗi JsonDecoder ", e) 
                    return
            else:
                self.check_mission = False
                self.robot.mesenger = f"Line {task_magazine['line']} mất kết nối với AMR. Xe di chuyển về vị trí chờ"
                
                return 
            
        elif (task_magazine['type'] == 'unload') and (task_magazine['floor'] == 1) and (task_magazine['vt'] == 'sau'):
            data = line_unloader.listen() 
            if data:
                try:
                    data_dict = json.loads(data)
                    if data_dict['floor1_sau']  == 0:
                        self.check_mission = False
                        self.robot.mesenger = "Magazine Đã Được Nhân Viên Trong Nhà Máy Lấy. AMR Di Chuyển Chờ Nhiệm Vụ"
                        if self.magazine_mission['line'] in AREA1:
                            self.robot.navigation({'id':"LM101"})
                        else:
                            self.robot.navigation({'id':STANDBY})
                            return 
                except json.JSONDecodeError as e:
                    self.check_mission = False
                    self.robot.mesenger = "Lỗi JsonDecoder: " + str(e)
                    logging.error("Lỗi JsonDecoder ", e)
                    return
            else:
                self.check_mission = False
                self.robot.mesenger = f"Line {task_magazine['line']} mất kết nối với AMR. Xe di chuyển về vị trí chờ"
                
                return 
        if task_magazine['floor'] == 1:
            self.robot.mesenger = f'Băng tải di chuyển xuống tầng 1 với độ cao {task_magazine["height"]}'
        else:
            self.robot.mesenger = f'Băng tải di chuyển lên tầng 2 với độ cao {task_magazine["height"]}'
        
        self.server_modbus.datablock_input_register.setValues(address=0x03,values=[task_magazine['height']])
        while self.server_modbus.datablock_holding_register.getValues(address=0x02,count=1)!=[task_magazine['height']]:
            logging.info(self.server_modbus.datablock_holding_register.getValues(address=0x02,count=1))
            time.sleep(1)
        
        self.robot.mesenger = 'AMR bắt đầu tranfer magazine'
        self.magazine_info['mission'] = task_magazine['line']
        self.magazine_info['floor'] = task_magazine['floor']
        if task_magazine['type'] == 'unload':
            line_unloader.send(type='begin')
            if (task_magazine['floor'] == 1) and (task_magazine['vt'] == 'truoc'):
                self.tranfer_magazine(floor=1, vt='truoc', stopper=self.stopper.Back_On, conveyor=self.dir.ccw_in, type='unload',
                                      line_unloader=line_unloader, line_loader=line_loader)
            elif (task_magazine['floor'] == 1) and (task_magazine['vt'] == 'sau'):
                self.tranfer_magazine(floor=1, vt='sau', stopper=self.stopper.Front_On, conveyor=self.dir.cw_in, type='unload',
                                      line_unloader=line_unloader, line_loader=line_loader)
            elif (task_magazine['floor'] == 2) and (task_magazine['vt'] == 'truoc'):
                self.tranfer_magazine(floor=2, vt='truoc', stopper=self.stopper.Back_On, conveyor=self.dir.ccw_out, type='unload',
                                      line_unloader=line_unloader, line_loader=line_loader)
            elif (task_magazine['floor'] == 2) and (task_magazine['vt'] == 'sau'):
                self.tranfer_magazine(floor=2, vt='sau', stopper=self.stopper.Front_On, conveyor=self.dir.cw_out, type='unload',
                                      line_unloader=line_unloader, line_loader=line_loader)
            line_unloader.send(type='end')
        elif task_magazine['type'] == 'load':
            line_loader.send(type='begin')
            if (task_magazine['floor'] == 1) and (task_magazine['vt'] == 'truoc'):
                self.tranfer_magazine(floor=1, vt='truoc', stopper=self.stopper.Front_On, conveyor=self.dir.cw_out, type='load',
                                      line_unloader=line_unloader, line_loader=line_loader)
            elif (task_magazine['floor'] == 2) and (task_magazine['vt'] == 'truoc'):
                self.tranfer_magazine(floor=2, vt='truoc', stopper=self.stopper.Front_On, conveyor=self.dir.cw_in, type='load',
                                      line_unloader=line_unloader, line_loader=line_loader)
            line_loader.send(type='end')
        self.robot.mesenger = 'Dừng Băng Tải'
        self.server_modbus.datablock_input_register.setValues(address=0x05,values=self.dir.stop)
        while self.server_modbus.datablock_holding_register.getValues(address=0x04,count=1)[0] != self.dir.stop:
            logging.info(self.server_modbus.datablock_holding_register.getValues(address=0x04,count=1))
            time.sleep(1)
        self.robot.mesenger = 'Đóng Stopper'
        self.server_modbus.datablock_input_register.setValues(address=0x04,values=[self.stopper.All_Off])
        self.server_modbus.datablock_input_register.setValues(address=0x03,values=[100])
        self.robot.mesenger = 'Băng tải di chuyển đến độ cao 100'
        while self.server_modbus.datablock_holding_register.getValues(address=0x02,count=1)[0]!=100:
            logging.info(self.server_modbus.datablock_holding_register.getValues(address=0x02,count=1))
            time.sleep(1)
        self.robot.mesenger = 'AMR đã tranfer xong magazine'
    
    def load_data(self, line: str, type: str, vt: str, floor: int) -> None:
        data = info_line(line)
        data_dict = json.loads(data)
        data_dict = data_dict[0]
        self.magazine_mission = {
            'line': line,
            'type': type,
            'floor': floor,
            'vt': vt
        }

        if(vt == "truoc"):
            self.magazine_mission['id'] = data_dict[type]['point_truoc']
        elif(vt == "sau"):
            self.magazine_mission['id'] = data_dict[type]['point_sau']
        if floor == 1:
            self.magazine_mission['height'] = data_dict[type]['h1']
        elif floor == 2:
            self.magazine_mission['height'] = data_dict[type]['h2']

    def poll_mission(self):
        while True:
            if (self.magazine_status['mission']) and (self.magazine_status['mission'] in self.robot.line_auto_web):
                #print("self.magazine_status: ", self.magazine_status)
                self.robot.idle = False 
                if (self.magazine_status['mission'] == 'line41') or (self.magazine_status['mission'] == 'line41_truoc') or (self.magazine_status['mission'] == 'line41_sau'):
                    line_unloader = Line(host=H_LINE41_UNLOADER,port=5000)
                    line_loader = Line(host=H_LINE41_LOADER, port=5000)
                    self.Call['Call_Unload_L41'] = 1
                    self.Call['Call_Load_L41'] = 1
                    line_des = self.magazine_status['mission']
                elif (self.magazine_status['mission'] == 'line40') or (self.magazine_status['mission'] == 'line40_truoc') or (self.magazine_status['mission'] == 'line40_sau'):
                    line_unloader = Line(host=H_LINE40_UNLOADER,port=5000)
                    line_loader = Line(host=H_LINE40_LOADER, port=5000)
                    self.Call['Call_Unload_L40'] = 1
                    self.Call['Call_Load_L40'] = 1
                    line_des = self.magazine_status['mission']
                elif (self.magazine_status['mission'] == 'line27') or (self.magazine_status['mission'] == 'line27_truoc'):
                    line_unloader = Line(host=H_LINE27_UNLOADER,port=5000)
                    line_loader = Line(host=H_LINE27_LOADER, port=5000)
                    self.Call['Call_Unload_L27'] = 1
                    self.Call['Call_Load_L27'] = 1
                    line_des = self.magazine_status['mission']
                elif (self.magazine_status['mission'] == 'line25') or (self.magazine_status['mission'] == 'line25_truoc'):
                    line_unloader = Line(host=H_LINE25_UNLOADER,port=5000)
                    line_loader = Line(host=H_LINE25_LOADER, port=5000)
                    self.Call['Call_Unload_L25'] = 1
                    self.Call['Call_Load_L25'] = 1
                    line_des = self.magazine_status['mission']
                
                self.load_data(line=line_des,
                                type=self.magazine_status['type'],
                                vt=self.magazine_status['vt'],
                                floor=self.magazine_status['floor'])
                

                data = info_line(line_des)
                data_dict = json.loads(data)
                data_dict = data_dict[0]
                if self.magazine_status['type'] == 'unload':
                    data_signal = line_loader.listen()
                elif self.magazine_status['type'] == 'load':
                    data_signal = line_unloader.listen()
                if self.magazine_mission['line'] in LINE_TRUOC:
                    if data_signal != "":
                        data_dict_signal = json.loads(data_signal)
                        #START------------Check sensor băng tải ở đây ----------------------
                        if self.robot.data_Status['sensors'][1] and self.robot.data_Status['sensors'][2]:
                            #END------------Check sensor băng tải ở đây ----------------------
                            if (data_dict_signal['floor2_truoc'] == 1):
                                self.check_sensor_conveyor = False
                                self.call_mission = True
                                self.history = {
                                    'mission': self.magazine_mission['line'],
                                    'floor': self.magazine_mission['floor'],
                                    'type': 'lay',
                                    'status': 'RUNNING'
                                }
                                #print("self.magazine_mission: ", self.magazine_mission)
                                self.run(task_magazine=self.magazine_mission, line_unloader=line_unloader, line_loader=line_loader)
                                self.magazine_mission['height'] = data_dict['unload']['h2']
                                if self.magazine_mission['type'] == "unload":
                                    self.magazine_mission['id'] = data_dict['load']['point_truoc']
                                    self.magazine_mission['type'] = 'load'
                                    self.magazine_mission['height'] = data_dict['load']['h1']
                                elif self.magazine_mission['type'] == "load":
                                    self.magazine_mission['id'] = data_dict['unload']['point_truoc']
                                    self.magazine_mission['type'] = 'unload'
                                    self.magazine_mission['vt'] = 'truoc'
                                else:
                                    logging.error("ERROR Type Magazine: ", self.magazine_mission['type'])
                                    raise TypeMagazineError("Type must unload or load")
                                if self.check_mission and self.robot.cancel == False:
                                    self.history = {
                                        'mission': self.magazine_mission['line'],
                                        'floor': self.magazine_mission['floor'],
                                        'type': 'tra',
                                        'status': "RUNNING"
                                    }
                                    self.run(task_magazine=self.magazine_mission, line_unloader=line_unloader, line_loader=line_loader)
                                    self.robot.mesenger = f"AMR Thực Hiện Xong Nhiệm Vụ {self.magazine_mission['line']}"
                            else:
                                self.call_mission = False
                        else:
                            if(not self.check_sensor_conveyor):
                                self.robot.mesenger = "Băng tải đang có hàng, AMR không di chuyển"
                                self.check_sensor_conveyor = True
                    else:
                        logging.error("ERROR SIGNAL ", self.magazine_mission['line'])
                elif self.magazine_mission['line'] in LINE_SAU:
                    if data_signal != "":
                        data_dict_signal = json.loads(data_signal)
                        #START------------Check sensor băng tải ở đây ----------------------
                        if self.robot.data_Status['sensors'][1] and self.robot.data_Status['sensors'][2]:
                            #END------------Check sensor băng tải ở đây ----------------------
                            if (data_dict_signal['floor2_sau'] == 1):
                                self.call_mission = True
                                self.check_sensor_conveyor = False
                                self.history = {
                                    'mission': self.magazine_mission['line'],
                                    'floor': self.magazine_mission['floor'],
                                    'type': 'lay',
                                    'status': 'RUNNING'
                                }
                                self.run(task_magazine=self.magazine_mission, line_unloader=line_unloader, line_loader=line_loader)
                                self.magazine_mission['height'] = data_dict['unload']['h2']
                                if self.magazine_mission['type'] == "unload":
                                    self.magazine_mission['id'] = data_dict['load']['point_sau']
                                    self.magazine_mission['type'] = 'load'
                                    self.magazine_mission['height'] = data_dict['load']['h1']
                                elif self.magazine_mission['type'] == "load":
                                    self.magazine_mission['id'] = data_dict['unload']['point_sau']
                                    self.magazine_mission['type'] = 'unload'
                                    self.magazine_mission['vt'] = 'truoc'
                                else:
                                    logging.error("ERROR Type Magazine: ", self.magazine_mission['type'])
                                    raise TypeMagazineError("Type must unload or load")
                                if self.check_mission and self.robot.cancel == False:
                                    self.history = {
                                        'mission': self.magazine_mission['line'],
                                        'floor': self.magazine_mission['floor'],
                                        'type': 'tra',
                                        'status': 'RUNNING'
                                    }
                                    self.run(task_magazine=self.magazine_mission, line_unloader=line_unloader, line_loader=line_loader)
                                    self.robot.mesenger = f"AMR Thực Hiện Xong Nhiệm Vụ {self.magazine_mission['line']}"
                            else:
                                self.call_mission = False
                        else:
                            if(not self.check_sensor_conveyor):
                                self.robot.mesenger = "Băng tải đang có hàng, AMR không di chuyển"
                                self.check_sensor_conveyor = True

                    else:
                        logging.error("ERROR SIGNAL ", self.magazine_mission['line'])
                    
                else:
                    logging.error("ERROR name Line: ", self.magazine_mission['line'])
                    raise LineNameMagazineError("Line name must Line25, Line27, Line40, Line41")
                self.robot.idle = True
                self.error = False
                if self.call_mission:
                    if (self.magazine_mission['line'] in AREA1):
                        self.robot.navigation({'id':"LM101"})
                    else:
                        self.robot.navigation({'id':STANDBY})
                self.magazine_info = {
                    'mission': '',
                    'floor': 0
                }
                self.magazine_status = {
                    'type' : '',
                    'mission' : '',
                    'vt': '',
                    'floor': 0,
                    'busy' : 0
                }

                self.history = {
                    'mission': '',
                    'floor': 0,
                    'type': '',
                    'status': ''
                }

                self.Call = {
                    'Call_Unload_L40' : -1,
                    'Call_Load_L40' : -1,
                    'Call_Unload_L41' : -1,
                    'Call_Load_L41' : -1,
                    'Call_Unload_L25' : -1,
                    'Call_Load_L25' : -1,
                    'Call_Unload_L27' : -1,
                    'Call_Load_L27' : -1
                }
                self.robot.mesenger = "AMR Thực Hiện Xong Nhiệm Vụ Di Ve StandBy"
            time.sleep(1)
    
    def poll_status(self):
        count = 0
        while True:
                self.robot.status(self.robot.keys)
                if self.robot.data_Status['blocked'] or self.robot.data_Status['emergency'] or self.error:
                    self.server_modbus.datablock_input_register.setValues(1, self.color.red)
                    self.led = 'red'
                else:
                    # exit(0)
                    if self.robot.data_Status['battery_level'] < 0.2 or self.robot.data_Status['charging']:
                        self.server_modbus.datablock_input_register.setValues(1, self.color.yellow)
                        self.led = 'yellow'
                        if (self.robot.data_Status['battery_level'] < 0.15) and self.robot.idle and count == 0:
                            count = 1
                            self.robot.mode = "manual"
                            self.robot.line_auto_web = ['line25','line27','line40', 'line41']
                            self.robot.navigation({'id':CHARGE})
                            self.robot.mesenger = "AMR di chuyển tới vị trí sạc"
                        if self.robot.data_Status["charging"] and count == 0:
                            count = 1
                            self.robot.mode = "manual"
                            self.robot.line_auto_web = ['line25','line27','line40', 'line41']
                        if (self.robot.data_Status['battery_level'] > 0.8) and self.robot.data_Status['current_station'] == CHARGE:
                            count = 1
                            self.robot.mode = "auto"
                            self.robot.line_auto_web = ["line40_truoc", "line41_truoc"]
                            self.robot.navigation({'id':STANDBY})
                            self.robot.mesenger = "AMR di chuyển tới vị trí StandBu"
                            self.server_modbus.datablock_input_register.setValues(1, self.color.green)
                            time.sleep(20)

                    else:
                        count = 0
                        self.server_modbus.datablock_input_register.setValues(1, self.color.green)
                        self.led = 'green'
                self.robot.data_Status['led'] = self.led
                self.robot.data_Status['mode'] = self.robot.mode
                self.robot.data_Status['line_auto_web'] = self.robot.line_auto_web
                self.robot.data_Status['message'] = self.robot.mesenger
                self.robot.data_Status['callStatus'] = self.Call
                self.robot.data_Status['magazine_status'] = self.magazine_info
                self.robot.data_Status['sensors'] = self.server_modbus.datablock_holding_register.getValues(address=0x0A, count=10)
                self.robot.data_Status['history'] = self.history
                self.robot.data_Status['idle'] = self.robot.idle
            # time.sleep(1)



