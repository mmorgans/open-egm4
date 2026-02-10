import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

class DatabaseHandler:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            # Default to ~/.open-egm4/egm4_data.sqlite
            base_dir = Path.home() / ".open-egm4"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(base_dir / "egm4_data.sqlite")
        else:
            self.db_path = db_path
            
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()

        # Enable WAL mode for better concurrent access
        cursor.execute('PRAGMA journal_mode=WAL')

        # 1. Sessions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                notes TEXT
            )
        ''')

        # 2. Raw Readings Table (All fields from EGM payload)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                record_type TEXT,
                plot_id INTEGER,
                record_num INTEGER,
                co2 REAL,
                h2o REAL,
                temp_c REAL,
                pressure REAL,
                par REAL,
                humidity REAL,
                delta_co2 REAL,
                soil_resp_rate REAL,
                probe_type INTEGER,
                elapsed_time REAL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')

        # Migration: Add elapsed_time column if missing (for existing DBs)
        try:
            cursor.execute("ALTER TABLE readings ADD COLUMN elapsed_time REAL")
        except sqlite3.OperationalError:
            pass # Column likely already exists

        # 3. Processed Measurements (Client-side calculated Flux)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                plot_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                flux_result REAL,
                r_squared REAL,
                temperature_mean REAL,
                notes TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def create_session(self, notes: str = "") -> int:
        """Start a new data session."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sessions (notes) VALUES (?)', (notes,))
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def get_latest_session(self) -> Optional[tuple[int, str]]:
        """
        Get the ID and start timestamp of the most recent session.
        Returns None if no sessions exist.
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('SELECT id, start_time FROM sessions ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            return result if result else None
        except Exception as e:
            logging.error(f"Error getting latest session: {e}")
            return None

    def get_recent_sessions(self, limit: int = 10) -> List[tuple[int, str, str]]:
        """
        Get list of recent sessions (id, start_time, notes).
        Ordered by ID desc.
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('SELECT id, start_time, notes FROM sessions ORDER BY id DESC LIMIT ?', (limit,))
            # Convert to list of tuples
            results = [(r[0], r[1], r[2]) for r in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            logging.error(f"Error getting recent sessions: {e}")
            return []

    def insert_reading(self, session_id: int, data: Dict[str, Any]):
        """Insert a raw reading record."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        # Extract fields safely
        try:
            cursor.execute('''
                INSERT INTO readings (
                    session_id, timestamp, record_type, plot_id, record_num,
                    co2, h2o, temp_c, pressure, 
                    par, humidity, delta_co2, soil_resp_rate, probe_type, elapsed_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                data.get('timestamp') or datetime.datetime.now().isoformat(),
                data.get('type', ''),
                data.get('plot', 0),
                data.get('record', 0),
                data.get('co2_ppm', 0),
                data.get('h2o', 0),
                data.get('temp', 0) or data.get('rht', 0), # Fallback to rht if temp is missing (probe vs irga)
                data.get('atmp', 0),
                data.get('par', 0),
                data.get('rh', 0),
                data.get('dc', 0),
                data.get('sr', 0),
                data.get('probe_type', 0),
                data.get('dt', 0)
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"DB Insert Error: {e}")
        finally:
            conn.close()

    def get_session_readings(self, session_id: int) -> List[Dict]:
        """Retrieve all readings for a session (for export)."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM readings WHERE session_id = ? ORDER BY id', (session_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def insert_measurement(self, session_id: int, plot_id: int, start_time: datetime.datetime, end_time: datetime.datetime, result: Any, notes: str = ""):
        """Insert a calculated flux measurement."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO measurements (
                    session_id, plot_id, start_time, end_time, 
                    flux_result, r_squared, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                plot_id,
                start_time.isoformat(),
                end_time.isoformat(),
                result.flux,
                result.r_squared,
                notes
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"DB Measurement Insert Error: {e}")
        finally:
            conn.close()
