from socket import socket
from frame import tranmit
from api import status, navigation, control, other

import socket
import logging
import time

format_HMS = '%H:%M:%S'

class Color:
    red=8
    green=2
    yellow=10
    green_blink=11

class Stopper:
    Back_Off = 1
    Back_On = 2
    Front_Off = 3
    Front_On = 4
    All_On = 6
    All_Off = 5
    
class Dir:
    stop=0
    cw_in=1
    ccw_in=2
    cw_out=3
    ccw_out=4

class ESA_API:
    def __init__(self,host:str):
        self.host = host
        self.apiRobotStatus     = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.apiRobotNavigation = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.apiRobotOther      = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.apiRobotConfig      = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.apiRobotControl      = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        self.data_Status={}
        self.keys = {
            "keys":["confidence","DI","DO","current_station","charging","last_station","vx","vy","blocked","block_reason","battery_level","task_status","target_id","emergency","reloc_status","fatals","errors","warnings","notices","current_ip",'x','y','fork_height','area_ids', "angle", "target_dist", "path", "unfinished_path"],
            "return_laser":False,
            "return_beams3D":False
        }

        self.conveyor ={
            'type':Dir.stop,
            'height':0.00
        }

        self.mission_list =[]
        self.mesenger=""
        self.mode = 'manual'
        # self.mode = 'auto'
        self.line_auto_web = ['line25','line27','line40', 'line41']
        self.idle = True
        self.cancel = False
    
    def connect_all(self):
        self.apiRobotStatus.settimeout(10)
        self.apiRobotStatus.connect((self.host,19204))
        self.apiRobotNavigation.settimeout(10)
        self.apiRobotNavigation.connect((self.host,19206))
        self.apiRobotOther.settimeout(10)
        self.apiRobotOther.connect((self.host,19210))
        self.apiRobotConfig.settimeout(10)
        self.apiRobotConfig.connect((self.host,19207))
        self.apiRobotControl.settimeout(10)
        self.apiRobotControl.connect((self.host,19205))

    def connect_status(self):
        self.apiRobotStatus.settimeout(10)
        self.apiRobotStatus.connect((self.host,19204))

    def connect_navigation(self):
        self.apiRobotNavigation.settimeout(10)
        self.apiRobotNavigation.connect((self.host,19206))

    def connect_other(self):
        self.apiRobotOther.settimeout(10)
        self.apiRobotOther.connect((self.host,19210))

    def connect_config(self):
        self.apiRobotConfig.settimeout(10)
        self.apiRobotConfig.connect((self.host,19207))
        
    def connect_control(self):
        self.apiRobotControl.settimeout(10)
        self.apiRobotControl.connect((self.host,19205))

    def navigation(self,jsonstring:dict):
        result = tranmit.sendAPI(self.apiRobotNavigation, navigation.robot_task_gotarget_req, jsonstring)
        logging.info(result)
        # while result['ret_code'] != 0:
        #     result = tranmit.sendAPI(self.apiRobotNavigation, navigation.robot_task_gotarget_req, jsonstring)
            
        return True

    def status(self,key):
        self.data_Status = tranmit.sendAPI(self.apiRobotStatus, status.robot_status_all1_req, key)
    
    def confirm_local(self):
        return tranmit.sendAPI(self.apiRobotControl,control.robot_control_comfirmloc_req,{})
    
    def relocation(self,data_possition:True):
        print(data_possition)
        return tranmit.sendAPI(self.apiRobotControl, control.robot_control_reloc_req,data_possition)
    
    def setDO(self,DO_json:dict):
        return tranmit.sendAPI(self.apiRobotOther,other.robot_other_setdo_req,DO_json)
    
    def check_target(self,data_status:dict, target:str):
        if(data_status['task_status'] == 4):
            if(data_status['current_station']) == target:
                return True
            else:
                return False
        else:
            return False

    def nav_cancel(self):
        return tranmit.sendAPI(self.apiRobotNavigation,navigation.robot_task_cancel_req,{})
    
    def nav_pause(self):
        return tranmit.sendAPI(self.apiRobotNavigation,navigation.robot_task_pause_req,{})

    def nav_resume(self):
        return tranmit.sendAPI(self.apiRobotNavigation,navigation.robot_task_resume_req,{})
    
    def monitor(self, data:dict):
        return tranmit.sendAPI(self.apiRobotControl,control.robot_control_motion_req, data)
    

