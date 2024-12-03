from line import Line
from uuid import uuid4
from config import *
from modbus_server import ModbusServer
from control import ESA_API, Stopper, Dir, Color


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
        self.call = {
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

    def transfer_magazine(self, floor:int, vt: str, stopper: int, conveyor: int, type: str,
                        line_unloader: Line, line_loader: Line) -> None:
        self._set_stopper(stopper)
        self._start_transfer(floor, vt, type, line_unloader, line_loader)
        self._run_conveyor(conveyor, floor, type)
        self._check_floor_transfer(floor, vt, type, line_unloader, line_loader)
        
    def _set_stopper(self, stopper: int) -> None:
        self.server_modbus.datablock_input_register.setValues(address=0x04, values=[stopper])
        while self.server_modbus.datablock_holding_register.getValues(address=0x03,count=1) != [stopper]:
            logging.info(self.server_modbus.datablock_holding_register.getValues(address=0x03,count=1))
            time.sleep(1)

    def _start_transfer(self, floor: int, vt: str, type: str, line_unloader: Line, line_loader: Line) -> None:
        if type == "unload":
            line_unloader.send(floor=floor, vt=vt, type=type, status='start')
        else:
            line_loader.send(floor=floor, vt=vt, type=type, status='start')

    def _run_conveyor(self, conveyor: int, floor: int, type: str) -> None:
        self.server_modbus.datablock_input_register.setValues(address=0x05, values=conveyor)
        if (type == 'unload' and floor == 1) or (type == 'load' and floor == 2):
            self._wait_for_conveyor(conveyor)

    def _check_floor_transfer(self, floor: int, vt: str, type: str, line_unloader: Line, line_loader: Line) -> None:
        if (type == 'unload' and floor == 2) or (type == 'load' and floor == 1):
            self._handle_floor_transfer(floor, vt, type, line_unloader, line_loader)
        self._complete_transfer(type, floor, vt, line_unloader, line_loader)

    def _wait_for_conveyor(self, conveyor: int) -> None:
        start_time = time.time()
        while self.server_modbus.datablock_holding_register.getValues(address=0x04,count=1)[0] != conveyor:
            if self._check_timeout(start_time):
                return
            logging.info(self.server_modbus.datablock_holding_register.getValues(address=0x04,count=1))
            time.sleep(1)

    def _check_timeout(self, start_time: float) -> bool:
        if (time.time() - start_time) > 20:
            self._handle_timeout()
            return True
        if self.robot.cancel:
            self._handle_cancel()
            return True
        return False

    def _handle_timeout(self) -> None:
        self.error = True
        self.robot.mesenger = "Ấn Nút Hủy Trên Màn Hình De RESET AMR"
        self.history['status'] = 'ERROR'
        self.server_modbus.datablock_input_register.setValues(address=0x05,values=self.dir.stop)

    def _handle_cancel(self) -> None:
        self.server_modbus.datablock_input_register.setValues(address=0x04,values=[self.stopper.All_Off])
        self.server_modbus.datablock_input_register.setValues(address=0x03,values=[100])
        self.robot.navigation({'id':STANDBY})

    def _complete_transfer(self, type: str, floor: int, vt: str, line_unloader: Line, line_loader: Line) -> None:
        self.history['status'] = 'SUCCESS'
        if type == "unload":
            line_unloader.send(floor=floor, vt=vt, type=type, status='stop')
        else:
            line_loader.send(floor=floor, vt=vt, type=type, status='stop')

    def run(self, task_magazine: dict, line_unloader: Line, line_loader: Line):
        if not self._prepare_run(task_magazine):
            return
            
        self._set_height(task_magazine)
        self._execute_transfer(task_magazine, line_unloader, line_loader)
        self._cleanup_run()

    def _prepare_run(self, task_magazine: dict) -> bool:
        self.check_mission = True
        self.robot.idle = False
        self.robot.cancel = False
        
        self.robot.navigation({
            'id': task_magazine['id'],
            'task_id': str(uuid4()),
            'source_id': "SELF_POSITION"
        })

        while not self.robot.check_target(self.robot.data_Status, task_magazine['id']):
            if self.robot.cancel:
                self._handle_cancel_navigation(task_magazine)
                return False
        return True

    def _set_height(self, task_magazine: dict) -> None:
        floor_text = "xuống tầng 1" if task_magazine['floor'] == 1 else "lên tầng 2"
        self.robot.mesenger = f'Băng tải di chuyển {floor_text} với độ cao {task_magazine["height"]}'
        
        self.server_modbus.datablock_input_register.setValues(address=0x03, values=[task_magazine['height']])
        self._wait_for_height(task_magazine['height'])

    def _execute_transfer(self, task_magazine: dict, line_unloader: Line, line_loader: Line) -> None:
        self.magazine_info.update({'mission': task_magazine['line'], 'floor': task_magazine['floor']})
        
        transfer_params = self._get_transfer_params(task_magazine)
        if not transfer_params:
            return
            
        line = line_unloader if task_magazine['type'] == 'unload' else line_loader
        line.send(type='begin')
        self.transfer_magazine(**transfer_params, line_unloader=line_unloader, line_loader=line_loader)
        line.send(type='end')

    def _get_transfer_params(self, task_magazine: dict) -> dict | None:
        params = {
            ('unload', 1, 'truoc'): {'stopper': self.stopper.Back_On, 'conveyor': self.dir.ccw_in},
            ('unload', 1, 'sau'): {'stopper': self.stopper.Front_On, 'conveyor': self.dir.cw_in},
            ('unload', 2, 'truoc'): {'stopper': self.stopper.Back_On, 'conveyor': self.dir.ccw_out},
            ('unload', 2, 'sau'): {'stopper': self.stopper.Front_On, 'conveyor': self.dir.cw_out},
            ('load', 1, 'truoc'): {'stopper': self.stopper.Front_On, 'conveyor': self.dir.cw_out},
            ('load', 2, 'truoc'): {'stopper': self.stopper.Front_On, 'conveyor': self.dir.cw_in}
        }
        
        key = (task_magazine['type'], task_magazine['floor'], task_magazine['vt'])
        if key not in params:
            return None
            
        return {**params[key], 'floor': task_magazine['floor'], 
                'vt': task_magazine['vt'], 'type': task_magazine['type']}

    def _cleanup_run(self) -> None:
        cleanup_steps = [
            ('Dừng Băng Tải', 0x05, self.dir.stop, 0x04),
            ('Đóng Stopper', 0x04, [self.stopper.All_Off], None),
            ('Băng tải di chuyển đến độ cao 100', 0x03, [100], 0x02)
        ]
        
        for msg, addr, val, check_addr in cleanup_steps:
            self.robot.mesenger = msg
            self.server_modbus.datablock_input_register.setValues(address=addr, values=val)
            if check_addr:
                self._wait_for_value(check_addr, val[0] if isinstance(val, list) else val)

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
            if not self._should_process_mission():
                time.sleep(1)
                continue
                
            self._process_mission()
            time.sleep(1)

    def _should_process_mission(self) -> bool:
        return (self.magazine_status['mission'] and 
                self.magazine_status['mission'] in self.robot.line_auto_web)

    def _process_mission(self) -> None:
        self.robot.idle = False
        line_pair = self._get_line_pair()
        if not line_pair:
            return

        line_unloader, line_loader = line_pair
        self._setup_mission()
        self._execute_mission(line_unloader, line_loader)
        self._cleanup_mission()

    def _get_line_pair(self) -> tuple[Line, Line] | None:
        line_configs = {
            'line41': (H_LINE41_UNLOADER, H_LINE41_LOADER, 'Call_L41'),
            'line40': (H_LINE40_UNLOADER, H_LINE40_LOADER, 'Call_L40'),
            'line27': (H_LINE27_UNLOADER, H_LINE27_LOADER, 'Call_L27'),
            'line25': (H_LINE25_UNLOADER, H_LINE25_LOADER, 'Call_L25')
        }

        for prefix, (h_unloader, h_loader, call) in line_configs.items():
            if self.magazine_status['mission'].startswith(prefix):
                self.call[f'Call_Unload_{call}'] = 1
                self.call[f'Call_Load_{call}'] = 1
                return Line(host=h_unloader, port=5000), Line(host=h_loader, port=5000)
        return None

    def _setup_mission(self) -> None:
        self.load_data(
            line=self.magazine_status['mission'],
            type=self.magazine_status['type'],
            vt=self.magazine_status['vt'],
            floor=self.magazine_status['floor']
        )

    def _execute_mission(self, line_unloader: Line, line_loader: Line) -> None:
        if not self._validate_mission(line_unloader, line_loader):
            return
            
        self.run(self.magazine_mission, line_unloader, line_loader)

    def _cleanup_mission(self) -> None:
        self.robot.idle = True
        self.error = False
        if self.call_mission:
            self._return_to_standby()
        self._reset_mission_state()

    def _return_to_standby(self) -> None:
        if (self.magazine_mission['line'] in AREA1):
            self.robot.navigation({'id':"LM101"})
        else:
            self.robot.navigation({'id':STANDBY})

    def _reset_mission_state(self) -> None:
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

        self.call = {
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

    def poll_status(self):
        while True:
            self.robot.status(self.robot.keys)
            self._update_led_status()
            self._update_robot_status()

    def _update_led_status(self) -> None:
        if self._is_error_state():
            self._set_led('red')
        elif self._is_battery_low():
            self._handle_battery_status()
        else:
            self._set_led('green')

    def _is_error_state(self) -> bool:
        return (self.robot.data_Status['blocked'] or 
                self.robot.data_Status['emergency'] or 
                self.error)

    def _is_battery_low(self) -> bool:
        return (self.robot.data_Status['battery_level'] < 0.2 or 
                self.robot.data_Status['charging'])

    def _handle_battery_status(self) -> None:
        self._set_led('yellow')
        if self._should_charge():
            self._start_charging()
        elif self._is_charged():
            self._resume_operation()

    def _set_led(self, color: str) -> None:
        self.server_modbus.datablock_input_register.setValues(1, getattr(self.color, color))
        self.led = color

    def _update_robot_status(self) -> None:
        self.robot.data_Status.update({
            'led': self.led,
            'mode': self.robot.mode,
            'line_auto_web': self.robot.line_auto_web,
            'message': self.robot.mesenger,
            'callStatus': self.call,
            'magazine_status': self.magazine_info,
            'sensors': self.server_modbus.datablock_holding_register.getValues(address=0x0A, count=10),
            'history': self.history,
            'idle': self.robot.idle
        })