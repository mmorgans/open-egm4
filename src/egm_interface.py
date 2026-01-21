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
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_TWO,
            timeout=0.1  # Non-blocking read
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
                # Only log/sleep if we're still running (not shutting down)
                if self.running:
                    logging.error(f"Loop error: {e}")
                    if self.error_callback:
                        self.error_callback(str(e))
                    await asyncio.sleep(0.5)
                else:
                    # Shutting down - exit immediately
                    break

    # _parse_data method is identical to previous implementation, 
    # but pasted here to complete the class replacement
    def _parse_data(self, line: str) -> dict:
        """
        Parses a raw line from the EGM-4.
        
        Record Structure (60+ digits, no spaces):
        Pos 0:     M/R (M=Real Time, R=Memory)
        Pos 1-2:   Plot No (0-99)
        Pos 3-6:   Rec No (1-9999)
        Pos 7-8:   Day (1-31)
        Pos 9-10:  Month (1-12)
        Pos 11-12: Hour (1-24)
        Pos 13-14: Minutes (0-59)
        Pos 15-19: CO2 Ref (ppm, 5 chars)
        Pos 20-24: H2O Ref (mb, 5 chars, 0 if no sensor)
        Pos 25-29: RHT (RH sensor temp, 000.0 format)
        Pos 30-33: A (probe-specific)
        Pos 34-37: B (probe-specific)
        Pos 38-41: C (probe-specific)
        Pos 42-45: D (probe-specific)
        Pos 46-49: E (probe-specific)
        Pos 50-53: F (probe-specific)
        Pos 54-55: G (probe-specific)
        Pos 56-57: H (probe-specific)
        Pos 58-60: AP (Atmospheric Pressure, mb)
        Pos 61-62: PT (Probe Type)
        """
        data = {}
        try:
            # Check for valid R or M record
            if len(line) >= 20 and line[0] in ('R', 'M'):
                data['type'] = line[0]
                
                # Core fields (always present)
                data['plot'] = int(line[1:3])
                data['record'] = int(line[3:7])
                data['day'] = int(line[7:9])
                data['month'] = int(line[9:11])
                data['hour'] = int(line[11:13])
                data['minute'] = int(line[13:15])
                data['co2_ppm'] = int(line[15:20])
                
                # H2O Ref (pos 20-24)
                if len(line) >= 25:
                    try:
                        data['h2o'] = int(line[20:25])
                    except ValueError:
                        data['h2o'] = 0
                
                # RHT - RH sensor temperature (pos 25-29, format 000.0)
                if len(line) >= 30:
                    try:
                        data['rht'] = float(line[25:30]) / 10.0
                    except ValueError:
                        data['rht'] = 0.0
                
                # Get probe type from end of record (last 2 chars)
                probe_type = 0
                if len(line) >= 62:
                    try:
                        probe_type = int(line[60:62])
                    except ValueError:
                        # Try last 2 chars if 60:62 fails
                        try:
                            probe_type = int(line[-2:])
                        except:
                            probe_type = 0
                data['probe_type'] = probe_type
                
                # Parse probe-specific fields A-H (pos 30-57)
                # A: 30-33, B: 34-37, C: 38-41, D: 42-45
                # E: 46-49, F: 50-53, G: 54-55, H: 56-57
                
                if probe_type == 8:
                    # SRC-1 Soil Respiration Chamber
                    # A: PAR (4 chars)
                    if len(line) >= 34:
                        try:
                            data['par'] = int(line[30:34])
                        except:
                            data['par'] = 0
                    
                    # B: %RH (4 chars)
                    if len(line) >= 38:
                        try:
                            data['rh'] = int(line[34:38])
                        except:
                            data['rh'] = 0
                    
                    # C: Temp (4 chars, format 000.0 -> divide by 10)
                    if len(line) >= 42:
                        try:
                            data['temp'] = float(line[38:42]) / 10.0
                        except:
                            data['temp'] = 0.0
                    
                    # D: DC - Delta CO2 (4 chars)
                    if len(line) >= 46:
                        try:
                            data['dc'] = int(line[42:46])
                        except:
                            data['dc'] = 0
                    
                    # E: DT - Delta Time (4 chars)
                    if len(line) >= 50:
                        try:
                            data['dt'] = int(line[46:50])
                        except:
                            data['dt'] = 0
                    
                    # F: SR Rate (4 chars, format 00.00 -> divide by 100)
                    if len(line) >= 54:
                        try:
                            sr_magnitude = float(line[50:54]) / 100.0
                        except:
                            sr_magnitude = 0.0
                        
                        # H: +/- SR sign (pos 56-57, 00=positive, 01=negative)
                        sr_sign = 1
                        if len(line) >= 58:
                            try:
                                if line[56:58] == '01':
                                    sr_sign = -1
                            except:
                                pass
                        data['sr'] = sr_magnitude * sr_sign
                    
                    # G: empty for SRC-1
                    
                elif probe_type == 0:
                    # No sensor - IRGA standalone (raw mV values)
                    if len(line) >= 34:
                        try:
                            data['mv_pin1'] = int(line[30:34])
                        except:
                            data['mv_pin1'] = 0
                    if len(line) >= 38:
                        try:
                            data['mv_pin2'] = int(line[34:38])
                        except:
                            data['mv_pin2'] = 0
                    if len(line) >= 42:
                        try:
                            data['mv_pin3'] = int(line[38:42])
                        except:
                            data['mv_pin3'] = 0
                    if len(line) >= 46:
                        try:
                            data['mv_pin4'] = int(line[42:46])
                        except:
                            data['mv_pin4'] = 0
                    if len(line) >= 50:
                        try:
                            data['mv_pin5'] = int(line[46:50])
                        except:
                            data['mv_pin5'] = 0
                
                # AP: Atmospheric Pressure (pos 58-60, 3 chars, in mb)
                if len(line) >= 61:
                    try:
                        data['atmp'] = int(line[58:61])
                    except:
                        data['atmp'] = 0
                
                # Device timestamp
                from datetime import datetime
                try:
                    data['device_timestamp'] = datetime(
                        year=datetime.now().year,
                        month=data['month'],
                        day=data['day'],
                        hour=data['hour'],
                        minute=data['minute']
                    )
                except:
                    data['device_timestamp'] = None
            
            elif len(line) > 0 and line[0] == 'B':
                # B-type record (alternate format)
                data['type'] = 'B'
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        data['co2_ppm'] = float(parts[2])
                    except:
                        pass
            
            elif len(line) > 0 and line[0] == 'W':
                # Warmup record: W,+NN (temperature in Celsius)
                # EGM is warming up, ready when temp reaches ~55C
                data['type'] = 'W'
                if ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            # Parse temperature value (e.g., "+54" -> 54)
                            temp_str = parts[1].replace('+', '').strip()
                            data['warmup_temp'] = float(temp_str)
                        except ValueError:
                            data['warmup_temp'] = 0
            
            elif len(line) > 0 and line[0] == 'Z':
                # Zero check record
                if ',' in line:
                    # Z,+N.N format - zero checking in progress (counts 0-14 seconds)
                    data['type'] = 'Z'
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            # Parse countdown value (e.g., "+10" or "+1.0" -> 10 or 1)
                            count_str = parts[1].replace('+', '').strip()
                            data['zero_countdown'] = float(count_str)
                        except ValueError:
                            data['zero_countdown'] = 0
                else:
                    # Plain "Z" - end of memory dump (not zero checking)
                    data['type'] = 'Z_END'
            
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
