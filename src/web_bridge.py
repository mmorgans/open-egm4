import asyncio
import logging
from typing import Optional

# Conditional import to allow this file to be parsed in standard Python
try:
    import js
    from pyodide.ffi import to_js
    HAS_WEB = True
except ImportError:
    HAS_WEB = False
    js = None

class WebSerialTransport:
    """
    Serial Transport Implementation for Web Serial API.
    Only works in PyScript/Pyodide environment.
    """
    def __init__(self):
        self._port = None
        self._reader = None
        self._writer = None
        self._is_open = False
        
        if not HAS_WEB:
            logging.warning("WebSerialTransport initialized outside of PyScript environment.")

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def in_waiting(self) -> int:
        # Web Serial doesn't expose in_waiting easily for Streams
        # We assume 1 to force read attempt if open
        return 1 if self._is_open else 0

    async def connect(self, port: str = None) -> bool:
        """
        Request port from user and connect.
        Note: `port` string argument is ignored as browser security involves a picker.
        """
        if not HAS_WEB:
            return False
            
        try:
            # Request Port (Must be triggered by user gesture in JS, need to ensure this call stack matches)
            # In Textual, message handlers are usually async tasks, might lose "User Activation" status?
            # If so, we might need a JS-side button to trigger this first.
            # But let's try calling it.
            
            # js.navigator.serial.requestPort() returns a Promise resolving to Port
            port_obj = await js.navigator.serial.requestPort()
            self._port = port_obj
            
            # Open the port
            # Baud 9600...
            options = to_js({"baudRate": 9600, "bufferSize": 2048})
            await self._port.open(options)
            
            self._is_open = True
            
            # Setup Reader
            # self._port.readable is a ReadableStream
            # We want to lock it to a reader
            self._reader = self._port.readable.getReader()
            
            # Writer
            if self._port.writable:
                 self._writer = self._port.writable.getWriter()
            
            return True
        except Exception as e:
            logging.error(f"Web Serial Connect Error: {e}")
            self._is_open = False
            return False

    async def disconnect(self) -> None:
        if not self._is_open:
            return
            
        try:
            if self._reader:
                await self._reader.cancel()
                self._reader.releaseLock()
            
            if self._writer:
                self._writer.releaseLock()
                
            await self._port.close()
        except Exception as e:
            logging.error(f"Disconnect error: {e}")
        finally:
            self._is_open = False
            self._port = None
            self._reader = None
            self._writer = None

    async def read(self, n: int) -> bytes:
        if not self._is_open or not self._reader:
            return b""
            
        try:
            # Read returns { value: Uint8Array, done: bool }
            result = await self._reader.read()
            if result.done:
                self._is_open = False
                return b""
                
            # Convert Uint8Array to bytes
            # Pyodide usually proxies Uint8Array to something buffer-like
            # .to_py() converts to memoryview/bytes
            chunk = result.value.to_py()
            return bytes(chunk)
            
        except Exception as e:
            logging.error(f"Read error: {e}")
            self._is_open = False
            return b""

    async def write(self, data: bytes) -> int:
        if not self._is_open or not self._writer:
            return 0
            
        try:
            # Create Uint8Array from bytes
            data_array = to_js(data)
            await self._writer.write(data_array)
            return len(data)
        except Exception as e:
            logging.error(f"Write error: {e}")
            return 0
