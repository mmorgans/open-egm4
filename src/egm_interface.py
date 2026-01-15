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
                    chunk = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                    buffer += chunk
                    
                    # Split on carriage returns (EGM-4 uses \r as record separator)
                    while '\r' in buffer:
                        record, buffer = buffer.split('\r', 1)
                        record = record.strip()
                        
                        if record:
                            parsed_data = self._parse_data(record)
                            if self.data_callback:
                                self.data_callback(record, parsed_data)
                else:
                    time.sleep(0.01)  # Prevent CPU spinning
            except Exception as e:
                logging.error(f"Read error: {e}")
                if self.error_callback:
                    self.error_callback(f"Read error: {e}")
                break

    def _parse_data(self, line: str) -> dict:
        """
        Parses a raw line from the EGM-4.
        
        Format: Fixed-width 61 characters
        Example: R000001180313170042900000000000000000000000000000000000096508
        
        Field positions:
        - type (1 char): line[0] - Record type ('R', 'B', or 'Z')
        - plot (2 chars): line[1:3]
        - record (4 chars): line[3:7]
        - day (2 chars): line[7:9]
        - month (2 chars): line[9:11]
        - hour (2 chars): line[11:13]
        - minute (2 chars): line[13:15]
        - co2_ppm (5 chars): line[15:20] - CO2 in ppm (e.g., '00429' = 429 ppm)
        - Additional fields follow...
        """
        data = {}
        
        try:
            # Check if this is a 61-character R-type record
            if len(line) >= 20 and line[0] == 'R':
                data['type'] = line[0]
                data['plot'] = int(line[1:3])
                data['record'] = int(line[3:7])
                data['day'] = int(line[7:9])
                data['month'] = int(line[9:11])
                data['hour'] = int(line[11:13])
                data['minute'] = int(line[13:15])
                
                # CO2 is the key value - 5 digits representing ppm
                co2_raw = line[15:20]
                data['co2_ppm'] = int(co2_raw)
                
                # Calculate timestamp from device time
                # Note: Year is not in the record, so we use current year
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
                    # Invalid date/time values
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
