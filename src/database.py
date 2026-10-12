import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any


def get_app_data_dir() -> Path:
    """Return the directory used for Open EGM-4 durable local data."""
    base_dir = Path.home() / ".open-egm4"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_log_dir() -> Path:
    """Return the directory used for raw serial logs."""
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


class DatabaseHandler:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            # Default to ~/.open-egm4/egm4_data.sqlite
            self.db_path = str(get_app_data_dir() / "egm4_data.sqlite")
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
                device_day INTEGER,
                device_month INTEGER,
                device_hour INTEGER,
                device_minute INTEGER,
                rht REAL,
                note TEXT,
                sample_id TEXT,
                sample_label TEXT,
                sample_ppm REAL,
                sample_peak_ppm REAL,
                raw_line TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')

        # Migrations for existing databases. Keep these additive and tolerant so
        # old field laptops can upgrade without touching their existing data.
        migrations = [
            ("elapsed_time", "REAL"),
            ("device_day", "INTEGER"),
            ("device_month", "INTEGER"),
            ("device_hour", "INTEGER"),
            ("device_minute", "INTEGER"),
            ("rht", "REAL"),
            ("note", "TEXT"),
            ("sample_id", "TEXT"),
            ("sample_label", "TEXT"),
            ("sample_ppm", "REAL"),
            ("sample_peak_ppm", "REAL"),
            ("raw_line", "TEXT"),
        ]
        for column, column_type in migrations:
            try:
                cursor.execute(f"ALTER TABLE readings ADD COLUMN {column} {column_type}")
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

    def end_session(self, session_id: int) -> None:
        """Mark a data session as ended."""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE sessions SET end_time = ? WHERE id = ? AND end_time IS NULL',
                (datetime.datetime.now().isoformat(), session_id),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error ending session {session_id}: {e}")

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

    @staticmethod
    def _num_or_none(value: Any) -> float | None:
        """Convert blanks and malformed values to NULL-safe numbers."""
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _int_or_none(cls, value: Any) -> int | None:
        num = cls._num_or_none(value)
        if num is None:
            return None
        return int(num)

    @classmethod
    def _first_num(cls, *values: Any) -> float | None:
        for value in values:
            converted = cls._num_or_none(value)
            if converted is not None:
                return converted
        return None

    def insert_reading(self, session_id: int, data: Dict[str, Any]):
        """Insert a raw reading record."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        record_type = data.get('type', data.get('record_type', ''))
        sample_id = data.get('sample_id', '')

        # Extract fields safely
        try:
            cursor.execute('''
                INSERT INTO readings (
                    session_id, timestamp, record_type, plot_id, record_num,
                    co2, h2o, temp_c, pressure, 
                    par, humidity, delta_co2, soil_resp_rate, probe_type, elapsed_time,
                    device_day, device_month, device_hour, device_minute, rht,
                    note, sample_id, sample_label, sample_ppm, sample_peak_ppm, raw_line
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                data.get('timestamp') or datetime.datetime.now().isoformat(),
                record_type,
                self._int_or_none(data.get('plot', data.get('plot_id'))),
                self._int_or_none(data.get('record', data.get('record_num'))),
                self._num_or_none(data.get('co2_ppm', data.get('co2'))),
                self._num_or_none(data.get('h2o', data.get('h2o_mb'))),
                self._first_num(data.get('temp'), data.get('temp_c')),
                self._num_or_none(data.get('atmp', data.get('atmp_mb'))),
                self._num_or_none(data.get('par')),
                self._num_or_none(data.get('rh', data.get('rh_pct'))),
                self._num_or_none(data.get('dc', data.get('dc_ppm'))),
                self._num_or_none(data.get('sr', data.get('sr_rate'))),
                self._int_or_none(data.get('probe_type')),
                self._num_or_none(data.get('dt', data.get('dt_s'))),
                self._int_or_none(data.get('day')),
                self._int_or_none(data.get('month')),
                self._int_or_none(data.get('hour')),
                self._int_or_none(data.get('minute')),
                self._num_or_none(data.get('rht', data.get('rht_c'))),
                data.get('note', ''),
                '' if sample_id in (None, '') else str(sample_id),
                data.get('sample_label', ''),
                self._num_or_none(data.get('sample_ppm')),
                self._num_or_none(data.get('sample_peak_ppm')),
                data.get('raw_line', ''),
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"DB Insert Error: {e}")
            raise
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
                getattr(result, "flux", getattr(result, "slope", 0.0)),
                result.r_squared,
                notes
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"DB Measurement Insert Error: {e}")
        finally:
            conn.close()
