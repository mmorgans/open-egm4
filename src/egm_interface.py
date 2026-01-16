import asyncio
import logging
import serial
import serial.tools.list_ports
from typing import Optional, Protocol, Callable, Any

# Protocol definition for what a "Serial Port" looks like to our app
class SerialTransport(Protocol):
    async def connect(self, port: str) -> bool: ...
    async def disconnect(self) -> None: ...
    async def read(self, n: int) -> bytes: ...
    async def write(self, data: bytes) -> int: ...
    @property
    def is_open(self) -> bool: ...
    @property
    def in_waiting(self) -> int: ...

class DesktopSerialTransport:
    """Standard PySerial implementation for Desktop use."""
    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._loop = asyncio.get_event_loop()

    @property
    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    @property
    def in_waiting(self) -> int:
        if self._serial:
            return self._serial.in_waiting
        return 0

    async def connect(self, port: str) -> bool:
        try:
            # Run blocking open in thread
            await self._loop.run_in_executor(None, self._connect_sync, port)
            return True
        except Exception as e:
            logging.error(f"Failed to connect: {e}")
            return False

    def _connect_sync(self, port: str):
        self._serial = serial.Serial(
            port=port,
            baudrate=9600,
            original_baudrate=9600, # pyserial-specific sometimes needed
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_TWO,
            timeout=0.1 # Non-blocking read preferred
        )

    async def disconnect(self) -> None:
        if self._serial:
            await self._loop.run_in_executor(None, self._serial.close)
            self._serial = None

    async def read(self, n: int) -> bytes:
        if not self._serial:
            return b""
        # Run blocking read in thread
        return await self._loop.run_in_executor(None, self._serial.read, n)

    async def write(self, data: bytes) -> int:
        if not self._serial:
            return 0
        return await self._loop.run_in_executor(None, self._serial.write, data)

class EGM4Serial:
    """
    High-level EGM-4 Interface.
    Agnostic to whether it's running on Desktop or Web.
    """
    def __init__(self, transport=None):
        self.transport = transport or DesktopSerialTransport()
        self.running = False
        self.buffer = ""
        
        # Callbacks
        self.data_callback: Optional[Callable[[str, dict], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None

    async def connect(self, port: str) -> bool:
        """Connects to the EGM-4 over serial."""
        success = await self.transport.connect(port)
        if success:
            self.running = True
            logging.info(f"Connected to {port}")
            return True
        else:
            if self.error_callback:
                self.error_callback(f"Failed to connect to {port}")
            return False

    async def disconnect(self):
        self.running = False
        await self.transport.disconnect()
        logging.info("Disconnected")

    async def process_loop(self):
        """Async loop to read and process data."""
        while self.running and self.transport.is_open:
            try:
                # Read chunks
                # We can't rely on in_waiting in all transports, so we just read small chunks
                # Or wait for data.
                if hasattr(self.transport, 'in_waiting') and self.transport.in_waiting > 0:
                     chunk = await self.transport.read(self.transport.in_waiting)
                else:
                     # Polling read if in_waiting not supported or empty
                     chunk = await self.transport.read(1024)
                     if not chunk:
                         await asyncio.sleep(0.01)
                         continue
                
                text_chunk = chunk.decode('utf-8', errors='ignore')
                self.buffer += text_chunk
                
                while '\r' in self.buffer:
                    record, self.buffer = self.buffer.split('\r', 1)
                    record = record.strip()
                    if record:
                        parsed = self._parse_data(record)
                        if self.data_callback:
                            self.data_callback(record, parsed)
                            
            except Exception as e:
                logging.error(f"Loop error: {e}")
                if self.error_callback:
                    self.error_callback(str(e))
                await asyncio.sleep(1)

    # _parse_data method is identical to previous implementation, 
    # but pasted here to complete the class replacement
    def _parse_data(self, line: str) -> dict:
        """Parses a raw line from the EGM-4."""
        data = {}
        try:
            if len(line) >= 20 and line[0] == 'R':
                data['type'] = line[0]
                data['plot'] = int(line[1:3])
                data['record'] = int(line[3:7])
                data['day'] = int(line[7:9])
                data['month'] = int(line[9:11])
                data['hour'] = int(line[11:13])
                data['minute'] = int(line[13:15])
                data['co2_ppm'] = int(line[15:20])
                
                if len(line) >= 61:
                    try:
                        data['probe_type'] = int(line[-2:])
                    except ValueError:
                        data['probe_type'] = 0
                
                # Basic/Extended fields
                if len(line) >= 25: data['h2o_ref'] = int(line[20:25])
                if len(line) >= 30: data['rht'] = int(line[25:30])
                if len(line) >= 58: data['pressure'] = int(line[54:58])

                # Probe 8 Logic
                pt = data.get('probe_type', 0)
                if pt == 8 or pt == 80:
                    data['par'] = int(line[30:34]) if len(line) >= 34 else 0
                    try: data['rh'] = int(line[34:39]) if len(line) >= 39 else 0
                    except: data['rh'] = 0
                    
                    if len(line) >= 43:
                         try: data['temp'] = float(line[39:43]) / 10.0
                         except: data['temp'] = 0
                    
                    if len(line) >= 47:  
                        try: data['dc'] = int(line[43:47])
                        except: data['dc'] = 0
                    if len(line) >= 51:
                         try: data['dt'] = int(line[47:51])
                         except: data['dt'] = 0
                    
                    if len(line) >= 55:
                        try: sr_mag = float(line[51:55]) / 100.0
                        except: sr_mag = 0
                        sr_sign = -1 if len(line)>59 and line[59]=='1' else 1
                        data['sr'] = sr_mag * sr_sign
                        
                    if len(line) >= 59:
                         try: 
                             data['atmp'] = int(line[55:59])
                             data['pressure'] = data['atmp']
                         except: pass

                else:
                    if len(line) >= 34: data['mv1'] = int(line[30:34])
                    if len(line) >= 38: data['mv2'] = int(line[34:38])
                    if len(line) >= 42: data['mv3'] = int(line[38:42]) 
                    if len(line) >= 46: data['mv4'] = int(line[42:46])
                    if len(line) >= 50: data['mv5'] = int(line[46:50])
                
                # Timestamp
                from datetime import datetime
                try:
                    data['device_timestamp'] = datetime(
                        year=datetime.now().year,
                        month=data['month'], day=data['day'],
                        hour=data['hour'], minute=data['minute']
                    )
                except: data['device_timestamp'] = None

            elif len(line) > 0 and line[0] == 'B':
                data['type'] = 'B'
                parts = line.split(',')
                if len(parts) >= 3:
                    try: data['co2_ppm'] = float(parts[2])
                    except: pass
            elif len(line) > 0 and line[0] == 'Z':
                data['type'] = 'Z'
            else:
                data['type'] = 'unknown'
                data['raw'] = line
        except Exception as e:
            data['error'] = str(e)
            data['raw'] = line
            
        return data

async def get_serial_ports():
    """Returns list of available serial ports."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_ports_sync)

def _get_ports_sync():
    return [p.device for p in serial.tools.list_ports.comports()]
