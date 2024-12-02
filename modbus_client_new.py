from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.exceptions import ModbusException, ConnectionException
from typing import List, Optional, Union
import time
import logging

class ModbusClient:  # Changed name to follow PEP 8
    """A wrapper class for Modbus TCP and RTU clients.
    
    Attributes:
        mb_host (str): Modbus server host address
        mb_port (int): Modbus server port
        mb_client (Union[ModbusTcpClient, ModbusSerialClient]): Modbus client instance
    """
    
    def __init__(self, host: Optional[str] = None, port: int = 502, client_type: str = 'tcp') -> None:
        """Initialize ModbusClient with connection parameters.
        
        Args:
            host: Server hostname or IP address
            port: Server port number (default: 502 for Modbus TCP)
            client_type: Type of connection ('tcp' or 'rtu')
        
        Raises:
            ValueError: If client_type is not 'tcp' or 'rtu'
        """
        self.mb_host = host
        self.mb_port = port
        
        if client_type.lower() == "tcp":
            self.mb_client = ModbusTcpClient(
                host=self.mb_host,
                port=self.mb_port,
                framer=ModbusSocketFramer
            )
        elif client_type.lower() == "rtu":
            self.mb_client = ModbusSerialClient(
                port='/dev/ttyUSB0',
                baudrate=19200,
                bytesize=8,
                stopbits=1,
                parity="O"
            )
            self.mb_client.connect()
        else:
            raise ValueError("client_type must be either 'tcp' or 'rtu'")

    def connect_to(self) -> bool:
        try:
            return bool(self.mb_client.connect())
        except (ModbusException, ConnectionException) as e:
            logging.error(f"Connection failed: {str(e)}")
            return False

    def reconnect_to(self) -> None:
        logging.info(f'Reconnecting to: {self.mb_host}')
        self.mb_client.close()
        
        while True:
            try:
                if self.mb_client.connect():
                    break
                logging.warning("Reconnection attempt failed, retrying in 10 seconds")
            except (ModbusException, ConnectionException) as e:
                logging.error(f"Reconnection error: {str(e)}")
                self.mb_client.close()
            time.sleep(10)

    def read_holding_reg(self, address: int, num_of_reg: int) -> List[int]:
        """Read holding registers from the Modbus server.
        
        Args:
            address: Starting address of registers
            num_of_reg: Number of registers to read
            
        Returns:
            List[int]: Register values or zeros if read fails
        """
        try:
            resp = self.mb_client.read_holding_registers(
                address=address,
                count=num_of_reg,
                slave=1
            )
            if resp.isError():
                raise ModbusException(f"Modbus error: {resp}")
            return resp.registers
        except (ModbusException, ConnectionException) as e:
            logging.error(f"Error reading holding registers: {str(e)}")
            self.reconnect_to()
            return [0] * num_of_reg

    def read_input_reg(self, address: int, num_of_reg: int) -> List[int]:
        """Read input registers from the Modbus server.
        
        Args:
            address: Starting address of registers
            num_of_reg: Number of registers to read
            
        Returns:
            List[int]: Register values or zeros if read fails
        """
        try:
            resp = self.mb_client.read_input_registers(
                address=address,
                count=num_of_reg,
                slave=1
            )
            if resp.isError():
                raise ModbusException(f"Modbus error: {resp}")
            return resp.registers
        except (ModbusException, ConnectionException) as e:
            logging.error(f"Error reading input registers: {str(e)}")
            self.reconnect_to()
            return [0] * num_of_reg

    def write_register(self, address: int, data: int) -> bool:
        """Write to a single register on the Modbus server.
        
        Args:
            address: Register address to write to
            data: Value to write
            
        Returns:
            bool: True if write successful, False otherwise
        """
        try:
            resp = self.mb_client.write_register(
                address=address,
                value=data,
                slave=1
            )
            return not resp.isError()
        except Exception as e:
            logging.error(f"Error writing to register: {str(e)}")
            self.reconnect_to()
            return False