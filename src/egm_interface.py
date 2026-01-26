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
        
        # Helper conversion functions
        def f10(x): return float(x) / 10.0
        def f100(x): return float(x) / 100.0
        
        # Define field mappings for different probe types based on EGM-4 Manual
        # Each tuple: (start_idx, end_idx, field_key, converson_func)
        PROBE_DEFINITIONS = {
            # Type 0: No Sensor (mV inputs)
            0: [
                (30, 34, 'aux1', int), (34, 38, 'aux2', int), (38, 42, 'aux3', int),
                (42, 46, 'aux4', int), (46, 50, 'aux5', int),
            ],
            # Type 1: STP-1 / CH15T (A=PAR, B=RH(f10), C=Temp(f10), E=mV5)
            1: [
                (30, 34, 'par', int),
                (34, 38, 'rh', f10),
                (38, 42, 'temp', f10),
                (46, 50, 'aux5', int),
            ],
            # Type 2: HTR-2 (A=PAR, B=RH(f10), C=Temp(f10))
            2: [
                (30, 34, 'par', int),
                (34, 38, 'rh', f10),
                (38, 42, 'temp', f10),
            ],
            # Type 3: HTR-1 (Same as Type 2)
            3: [
                (30, 34, 'par', int),
                (34, 38, 'rh', f10),
                (38, 42, 'temp', f10),
            ],
            # Type 7: PMR-4 Porometer
            7: [
                (30, 34, 'par', int),
                (34, 38, 'rh', f10), # RH In
                (38, 42, 'temp', f10),
                (42, 46, 'rh_out', f10), # RH Out
                (46, 50, 'flow', f10),   # Flow
                (50, 54, 'gs', int),     # GS
            ],
            # Type 8: SRC-1 Soil Respiration Chamber
            # Note: SRC-1 has NO PAR/RH/Temp sensors - columns A-C are always 0
            # Empirically verified positions (may differ from manual by 1 char):
            # - DC (Delta CO2) at [42:46] or could be at [43:47]
            # - DT/SR handled in post-processing from end of record
            8: [
                # DC and DT seem unreliable from fixed positions
                # SR and ATMP are parsed from END of record in post-processing
            ],
            # Type 11: CPY-3 / CFX-1 Open System
            11: [
                (30, 34, 'par', int),
                (34, 38, 'evap', int),                   # Evap Rate (0000)
                (38, 42, 'temp', f10),
                (42, 46, 'dc', int),
                (46, 50, 'flow', f10),                   # Flow (000.0)
                (50, 54, 'sr_mag', f100),
                (54, 55, 'flow_mult', int),              # G: Flow Mult
                (56, 58, 'sr_sign', str),
            ],
            # Type 0: IRGA Only (No Sensor Connected)
            # Positions 31-50 are raw mV from pins 1-5
            0: [
                (30, 34, 'aux1', int),   # mV Pin 1
                (34, 38, 'aux2', int),   # mV Pin 2
                (38, 42, 'aux3', int),   # mV Pin 3
                (42, 46, 'aux4', int),   # mV Pin 4
                (46, 50, 'aux5', int),   # mV Pin 5
            ],
            # Default/Generic (Probes 4, 5, 6, 9, 10, 13 etc)
            'default': [
                (30, 34, 'aux1', int),
                (34, 38, 'aux2', int),
                (38, 42, 'aux3', int),
                (42, 46, 'aux4', int),
                (46, 50, 'aux5', int),
            ]
        }

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
                # PT is always at the end of the record, positions vary by record length
                probe_type = 0
                try:
                    # PT is the last 2 characters of the record
                    probe_type = int(line[-2:])
                except ValueError:
                    probe_type = 0
                
                data['probe_type'] = probe_type
                
                # Parse probe-specific fields using definition
                defs = PROBE_DEFINITIONS.get(probe_type, PROBE_DEFINITIONS['default'])
                
                for start, end, key, func in defs:
                    if len(line) >= end:
                        try:
                            # Special handling for SR sign
                            if key == 'sr_sign':
                                # This is handled later/differently in original code, 
                                # but let's just parse it if present to helper var
                                pass 
                            else:
                                val_str = line[start:end]
                                data[key] = func(val_str)
                        except:
                            # Set default 0 or 0.0 based on func type? 
                            # Simplest is just 0
                            data[key] = 0

                # VERIFIED positions from end for SRC-1 (Type 8):
                #   PT   = line[-2:]    (2 chars) - Probe Type
                #   AP   = line[-6:-2]  (4 chars) - Atmospheric Pressure in mb
                #   ??   = line[-10:-6] (4 chars) - Padding/sign (0000)
                #   SR   = line[-14:-10](4 chars) - Soil Respiration rate (÷100 for gCO2/m2/hr)
                #   DT   = line[-18:-14](4 chars) - Delta Time in seconds (cumulative)
                #   DC   = line[-22:-18](4 chars) - Delta CO2 in ppm (cumulative)
                if probe_type == 8:
                    try:
                        # ATMP is 4 chars before PT
                        atmp_str = line[-6:-2]
                        data['atmp'] = int(atmp_str)
                    except:
                        data['atmp'] = 0
                    
                    try:
                        # SR (Soil Respiration rate)
                        sr_str = line[-14:-10]
                        sr_val = float(sr_str) / 100.0  # Convert to gCO2/m2/hr
                        data['sr'] = sr_val
                    except:
                        data['sr'] = 0.0
                    
                    try:
                        # DT (Delta Time in seconds, cumulative)
                        dt_str = line[-18:-14]
                        data['dt'] = int(dt_str)
                    except:
                        data['dt'] = 0
                    
                    try:
                        # DC (Delta CO2 in ppm, cumulative rise)
                        dc_str = line[-22:-18]
                        data['dc'] = int(dc_str)
                    except:
                        data['dc'] = 0
                
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
