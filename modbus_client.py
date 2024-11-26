from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.transaction import ModbusSocketFramer
import time

import logging
class Modbus_Client:
    def __init__(self,host:str=None,port:int=0, type: str='tcp') -> None:
        self.mb_host = host
        self.mb_port = port
        if type == "tcp":
            self.mb_client = ModbusTcpClient(host = self.mb_host,port = self.mb_port,framer=ModbusSocketFramer)
        elif type == "rtu":
            self.mb_client = ModbusSerialClient(port='/dev/ttyUSB0', baudrate=19200, bytesize=8, stopbits=1, parity="O")
            self.mb_client.connect()

    def connectTo(self) -> bool:
        try:
            if self.mb_client.connect():
                return True
            else:
                return False
        except Exception as e:
            logging.info(e)
            return False
    
    def reconnectTo(self):
        logging.info('reconnecting to : ' + self.mb_host)
        self.mb_client.close()
        while True:
            try:
                self.mb_client.connect()
                break
            except Exception as e:
                logging.info(e)
                self.mb_client.close()
            time.sleep(10)
    def readHoldingReg(self, address: int, numOfReg:int):
        try:
            resp = self.mb_client.read_holding_registers(address=address,count=numOfReg,slave=1)
            return resp.registers
        except:
            self.reconnectTo()
            return [0,0,0,0,0,0,0,0]
    def readInputReg(self, address: int, numOfReg:int):
        try:
            resp = self.mb_client.read_input_registers(address=address,count=numOfReg,slave=1)
            return resp.registers
        except:
            self.reconnectTo()
            return [0,0,0,0,0,0,0,0]
    
    def writeRegister(self,address:int,data:int):
        try:
            self.mb_client.write_register(address=address,value=data,slave=1)
            return True
        except:
            self.reconnectTo()
            return False
