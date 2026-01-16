import serial
import threading
import time
import logging
from datetime import datetime

class EGM4Serial:
    def __init__(self):
        self.serial_conn = None
        self.running = False
        self.read_thread = None
        self.data_callback = None # Function(raw_line: str, parsed_data: dict)
        self.error_callback = None # Function(error_msg: str)

    def connect(self, port: str):
        """Connects to the EGM-4 over serial."""
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=1
            )
            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            logging.info(f"Connected to {port}")
            return True
        except serial.SerialException as e:
            if self.error_callback:
                self.error_callback(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnects the serial connection."""
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
        logging.info("Disconnected")

    def _read_loop(self):
        """Background loop to read from serial port.
        
        The EGM-4 sends data in bursts with records separated by carriage returns (\\r).
        We need to buffer incoming data and split on \\r to get individual records.
        """
        buffer = ""
        
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                if self.serial_conn.in_waiting > 0:
                    # Read all available bytes
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    if not data:
                        # Spurious ready signal or timeout
                        time.sleep(0.01)
                        continue
                        
                    chunk = data.decode('utf-8', errors='ignore')
                    buffer += chunk
                    
                    # Split on carriage returns (EGM-4 uses \r as record separator)
                    while '\r' in buffer:
                        record, buffer = buffer.split('\r', 1)
                        record = record.strip()
                        
                        if record:
                            parsed_data = self._parse_data(record)
                            if self.data_callback:
                                try:
                                    self.data_callback(record, parsed_data)
                                except Exception as cb_err:
                                    logging.error(f"Callback error: {cb_err}")
                else:
                    time.sleep(0.01)  # Prevent CPU spinning
            except serial.SerialException as e:
                logging.error(f"Serial error: {e}")
                if self.error_callback:
                    self.error_callback(f"Serial Error: {e}")
                # If the device is truly gone, this will likely repeat, so breaking is okay
                # But sometimes it recovers. Let's break to be safe and force user to reconnect.
                break
            except OSError as e:
                logging.error(f"OS Read error: {e}")
                if "returned no data" in str(e):
                    # Known Mac Serial issue, ignore and retry
                    time.sleep(0.1)
                    continue
                if self.error_callback:
                    self.error_callback(f"OS Error: {e}")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                # Don't crash the thread for general parsing/logic errors
                time.sleep(0.5)

    def _parse_data(self, line: str) -> dict:
        """
        Parses a raw line from the EGM-4.
        
        Format: Fixed-width 61 characters for R-records
        Example: R000001180313170042900000000000000000000000000000000000096508
        
        Field positions (0-indexed):
        - type (1 char): line[0] - Record type ('R', 'B', or 'Z')
        - plot (2 chars): line[1:3]
        - record (4 chars): line[3:7]
        - day (2 chars): line[7:9]
        - month (2 chars): line[9:11]
        - hour (2 chars): line[11:13]
        - minute (2 chars): line[13:15]
        - co2_ppm (5 chars): line[15:20] - CO2 in ppm
        - h2o_ref (5 chars): line[20:25] - H2O reference
        - rht (5 chars): line[25:30] - RH/Temperature
        - mv1 (4 chars): line[30:34] - mVolt 1
        - mv2 (4 chars): line[34:38] - mVolt 2
        - mv3 (4 chars): line[38:42] - mVolt 3
        - mv4 (4 chars): line[42:46] - mVolt 4
        - mv5 (4 chars): line[46:50] - mVolt 5 (or padding)
        - reserved (4 chars): line[50:54]
        - pressure (4 chars): line[54:58] - Atmospheric pressure (mb)
        - probe_type (2 chars): line[58:60] - Probe type code
        """
        data = {}
        
        try:
            # Check if this is an R-type record (at least 20 chars for basic fields)
            if len(line) >= 20 and line[0] == 'R':
                data['type'] = line[0]
                data['plot'] = int(line[1:3])
                data['record'] = int(line[3:7])
                data['day'] = int(line[7:9])
                data['month'] = int(line[9:11])
                data['hour'] = int(line[11:13])
                data['minute'] = int(line[13:15])
                
                # CO2 - primary value
                data['co2_ppm'] = int(line[15:20])
                
                if len(line) >= 61:
                    # Probe type is last 2 chars (positions 58-60 in 0-indexed string, but string is 61 chars including type)
                    # Example format: ...AP..PT..
                    # R... (61 chars long usually)
                    # Indices:
                    # 54:58 = Pressure (AP)
                    # 58:60 = Probe Type (PT)
                    # 60 = likely ignored or part of PT if 2 chars?
                    # The user says "last 2 digits". In a 61 char string, that's 59:61.
                    # But Python slice [58:60] gets chars at 58 and 59.
                    # Let's count back from end to be safe.
                    try:
                        data['probe_type'] = int(line[-2:])  # Last 2 chars
                    except ValueError:
                        data['probe_type'] = 0
                
                # Extended fields based on Probe Type
                # Common fields first
                if len(line) >= 25:
                    data['h2o_ref'] = int(line[20:25])
                if len(line) >= 30:
                    data['rht'] = int(line[25:30])
                if len(line) >= 58:
                    data['pressure'] = int(line[54:58])

                # Variable Data Area (Columns A-H)
                # Rewritten based on precise analysis of screenlog.0:
                # Type 8 (SRC-1) Layout (indices 0-based):
                # A (30:34): PAR (4 chars)
                # B (34:38): %RH (4 chars)
                # C (38:42): Temp (4 chars) - implied decimal? manual "000.0" might just be format desc. assuming 4 digits.
                # D (42:46): DC (4 chars)
                # E (46:50): DT (4 chars)
                # F (50:55): SR Rate (Magnitude) (5 chars) -> "00000" in log.
                # G (55:59): ATMP (Pressure) (4 chars) -> "0965" in log.
                # H (59): Sign of SR Rate (1 char) -> "0" in "08".
                # PT (60): Probe Type (1 char) -> "8" in "08".
                
                # Check probe type first. 
                # If we parsed `probe_type` from `line[-2:]`, it would be `08`.
                # If parsed from `line[60]`, it would be `8`.
                # Both indicate Type 8.
                pt = data.get('probe_type', 0)
                
                if pt == 8 or pt == 80: # Just in case slicing was weird.
                    # Verified Offsets via debug script on screenlog.0:
                    # A: 30-34 (4 chars)
                    # B: 34-39 (5 chars?) or shifted. Let's assume 34-39 covers it.
                    # C: 39-43 (4 chars) -> "0051" -> 51 -> 5.1 C
                    # D: 43-47 (4 chars) -> "0057" -> 57 DC
                    # E: 47-51 (4 chars) -> "0082" -> 82 DT
                    # F: 51-55 (4 chars) -> "0000" -> 00.00 SR Mag
                    # G: 55-59 (4 chars) -> "0968" -> 968 ATMP
                    # H: 59    (1 char)  -> "0"    -> + Sign
                    # PT: 60   (1 char)  -> "8"    -> Type 8
                    
                    # A: PAR
                    data['par'] = int(line[30:34]) if len(line) >= 34 else 0
                    
                    # B: %RH (Assuming 5 chars or shifted space?)
                    # If C starts at 39, and A ends at 34... 34-39 is 5 chars.
                    try:
                        data['rh'] = int(line[34:39]) if len(line) >= 39 else 0
                    except ValueError:
                         data['rh'] = 0
                    
                    # C: Temp (4 chars: 39-43)
                    # Data "0051" -> 51 -> 5.1? Or "0000" -> 0.0
                    if len(line) >= 43:
                         try:
                             val = float(line[39:43])
                             data['temp'] = val / 10.0
                         except ValueError:
                             data['temp'] = 0.0
                    else:
                        data['temp'] = 0.0
                    
                    # D: DC (4 chars: 43-47)
                    if len(line) >= 47:
                        try:
                            data['dc'] = int(line[43:47])
                        except ValueError:
                            data['dc'] = 0
                    
                    # E: DT (4 chars: 47-51)
                    if len(line) >= 51:
                         try:
                             data['dt'] = int(line[47:51])
                         except ValueError:
                             data['dt'] = 0
                    
                    # F: SR Rate Magnitude (4 chars: 51-55)
                    sr_mag = 0.0
                    if len(line) >= 55:
                        try:
                            sr_mag = float(line[51:55]) / 100.0 # "0000" -> 0.00
                        except ValueError:
                            pass
                            
                    # G: ATMP (4 chars: 55-59)
                    if len(line) >= 59:
                         try:
                             data['atmp'] = int(line[55:59])
                             data['pressure'] = data['atmp']
                         except ValueError:
                             pass

                    # H: Sign (1 char: 59)
                    sr_sign = 1
                    if len(line) > 59:
                        sign_char = line[59]
                        if sign_char == '1': # 1 = -
                             sr_sign = -1
                        # 0 = + (default)
                    
                    data['sr'] = sr_mag * sr_sign
                
                else:
                    # Generic mapping (Type 0 / IRGA)
                    # A-E to mV1-5
                    if len(line) >= 34: data['mv1'] = int(line[30:34])
                    if len(line) >= 38: data['mv2'] = int(line[34:38])
                    if len(line) >= 42: data['mv3'] = int(line[38:42]) 
                    if len(line) >= 46: data['mv4'] = int(line[42:46])
                    if len(line) >= 50: data['mv5'] = int(line[46:50])
                    # Pressure usually at 54:58 for generic
                    if len(line) >= 58: 
                         data['pressure'] = int(line[54:58])
                         data['atmp'] = data['pressure']


                
                # Calculate timestamp from device time
                from datetime import datetime
                current_year = datetime.now().year
                try:
                    data['device_timestamp'] = datetime(
                        year=current_year,
                        month=data['month'],
                        day=data['day'],
                        hour=data['hour'],
                        minute=data['minute']
                    )
                except ValueError:
                    data['device_timestamp'] = None
                
                logging.debug(f"Parsed R-record: CO2={data['co2_ppm']} ppm, Record#{data['record']}")
                
            elif len(line) > 0 and line[0] == 'B':
                # B-type record (appears to be comma-separated)
                # Example: "B,EGM4,+329.0,+1.41"
                data['type'] = 'B'
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        data['co2_ppm'] = float(parts[2])
                        logging.debug(f"Parsed B-record: CO2={data['co2_ppm']} ppm")
                    except ValueError:
                        pass
                        
            elif len(line) > 0 and line[0] == 'Z':
                # Z-type record (end marker)
                data['type'] = 'Z'
                logging.debug("Parsed Z-record (end marker)")
            
            else:
                # Unknown format
                data['type'] = 'unknown'
                data['raw'] = line
                
        except Exception as e:
            logging.error(f"Parse error: {e} for line: {line}")
            data['error'] = str(e)
            data['raw'] = line
            
        return data
