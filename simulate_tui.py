#!/usr/bin/env python3
"""
Simulation script for testing the EGM-4 TUI without hardware.

This script mocks the serial interface to generate fake EGM-4 data,
allowing you to test the UI without a physical device connected.

Usage:
    ./venv/bin/python simulate_tui.py
"""

import sys
import threading
import time
import random
from unittest.mock import MagicMock

# Mock serial module before importing anything else
mock_serial = MagicMock()
sys.modules['serial'] = mock_serial
sys.modules['serial.tools'] = MagicMock()
sys.modules['serial.tools.list_ports'] = MagicMock()

# Setup mock ports
class MockPort:
    def __init__(self, device: str, description: str):
        self.device = device
        self.description = description

mock_ports = [
    MockPort("/dev/cu.usbserial-SIM001", "Simulated EGM-4 Device"),
    MockPort("/dev/cu.usbserial-SIM002", "Another Test Port"),
]
sys.modules['serial.tools.list_ports'].comports = MagicMock(return_value=mock_ports)

# Now we can import our modules
from src.egm_interface import EGM4Serial


class SimulatedEGM4Serial(EGM4Serial):
    """A mock version of EGM4Serial that generates fake data."""
    
    def __init__(self):
        super().__init__()
        self._sim_thread = None
        self._base_co2 = 400
    
    def connect(self, port: str) -> bool:
        """Simulate connection and start data generation."""
        self.running = True
        self._sim_thread = threading.Thread(target=self._generate_data, daemon=True)
        self._sim_thread.start()
        return True
    
    def disconnect(self) -> None:
        """Stop the simulation."""
        self.running = False
        if self._sim_thread:
            self._sim_thread.join(timeout=1.0)
    
    def _generate_data(self) -> None:
        """Generate fake EGM-4 data at ~1Hz."""
        record_count = 0
        
        while self.running:
            time.sleep(0.8 + random.random() * 0.4)  # ~1Hz with jitter
            
            record_count += 1
            
            # Simulate slowly changing CO2 with some noise
            self._base_co2 += random.uniform(-5, 8)
            self._base_co2 = max(350, min(800, self._base_co2))  # Clamp
            co2 = int(self._base_co2 + random.gauss(0, 3))
            
            # Format: R{plot}{record}{day}{month}{hour}{minute}{co2}...
            raw_line = f"R01{record_count:04d}15011430{co2:05d}" + "0" * 40
            
            parsed = {
                'type': 'R',
                'co2_ppm': co2,
                'record': record_count,
                'plot': 1,
                'day': 15,
                'month': 1,
                'hour': 14,
                'minute': 30,
            }
            
            if self.data_callback:
                try:
                    self.data_callback(raw_line, parsed)
                except Exception as e:
                    print(f"Callback error: {e}")
            
            # Occasionally simulate download complete
            if record_count > 0 and record_count % 50 == 0:
                if self.data_callback:
                    self.data_callback("Z", {'type': 'Z'})


# Monkey-patch the EGM4Serial class in the monitor module
import src.tui.screens.monitor as monitor_module
monitor_module.EGM4Serial = SimulatedEGM4Serial


def main():
    """Run the simulated TUI."""
    print("=" * 60)
    print("  EGM-4 TUI SIMULATION MODE")
    print("  Generating fake data - no hardware needed!")
    print("=" * 60)
    print()
    
    from src.tui.app import EGM4App
    
    app = EGM4App()
    app.run()


if __name__ == "__main__":
    main()
