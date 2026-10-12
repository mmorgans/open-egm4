"""Hardware-free checks of recording, display, and shutdown behavior."""
import asyncio
import csv
import sqlite3
import time
from pathlib import Path

import pytest

from src.database import DatabaseHandler
from src.tui.app import EGM4App
from src.tui.screens.monitor import DataReceived, MonitorScreen
from src.tui.screens.note import NoteInputScreen
from src.tui.widgets.co2_chart import CO2PlotWidget
from src.tui.widgets.stats import StatsWidget


class OfflineApp(EGM4App):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.monitor = MonitorScreen(None, db_handler=db)

    def on_mount(self):
        self.push_screen(self.monitor)


def reading(dt=0, co2=400, plot=1, kind="R"):
    data = dict(type=kind, plot=plot, record=1, co2_ppm=co2, probe_type=8)
    if dt is not None:
        data['dt'] = dt
    return data


def test_slope_uses_device_time_and_separates_cycles():
    monitor = MonitorScreen(None)
    assert monitor._update_slope(reading(0)) is None
    assert monitor._update_slope(reading(10, 420)).slope == 2
    assert monitor._update_slope(reading(0, 800, plot=2)) is None
    assert monitor._update_slope(reading(10, 800, plot=2)).slope == 0
    assert monitor._update_slope(reading(0, 900, plot=2)) is None
    assert monitor._update_slope(reading(None, kind="R")) is None
    monitor._writer.shutdown()


def test_pause_records_and_catches_up_chart(tmp_path):
    async def scenario():
        db = DatabaseHandler(str(tmp_path / 'data.sqlite'))
        app = OfflineApp(db)
        async with app.run_test() as pilot:
            monitor = app.monitor
            chart = monitor.query_one(CO2PlotWidget)
            monitor.action_pause()
            assert chart.is_paused
            for dt in (0, 10, 20):
                monitor.post_message(DataReceived('raw', reading(dt, 400 + dt)))
            await pilot.pause()
            await monitor._flush_writes()
            assert len(monitor.recorded_data) == 3
            assert len(db.get_session_readings(monitor.session_id)) == 3
            assert chart.current_dt == 20
            assert monitor.query_one(StatsWidget).current_co2 == 420
            monitor.action_pause()
            assert not chart.is_paused
    asyncio.run(scenario())


@pytest.mark.parametrize('modal', [False, True])
def test_quit_drains_writes_and_exports(tmp_path, monkeypatch, modal):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    downloads = tmp_path / 'Downloads'
    downloads.mkdir()

    class SlowDatabase(DatabaseHandler):
        def insert_reading(self, session_id, data):
            time.sleep(0.03)
            super().insert_reading(session_id, data)

    async def scenario():
        db = SlowDatabase(str(tmp_path / 'data.sqlite'))
        app = OfflineApp(db)
        async with app.run_test() as pilot:
            monitor = app.monitor
            for dt in range(6):
                monitor.post_message(DataReceived('raw', reading(dt)))
            await pilot.pause()
            if modal:
                await app.push_screen(NoteInputScreen())
                await pilot.press('ctrl+c')
            else:
                await pilot.press('q')
            await pilot.pause(0.5)
        assert len(db.get_session_readings(monitor.session_id)) == 6
        exports = list(downloads.glob('egm4_data_*.csv'))
        assert len(exports) == 1
        with exports[0].open() as f:
            assert len(list(csv.DictReader(f))) == 6
    asyncio.run(scenario())


def test_recording_failure_is_visible_and_csv_buffer_survives(tmp_path):
    class FailingDatabase(DatabaseHandler):
        def insert_reading(self, session_id, data):
            raise sqlite3.OperationalError('disk full')

    async def scenario():
        app = OfflineApp(FailingDatabase(str(tmp_path / 'data.sqlite')))
        async with app.run_test() as pilot:
            app.monitor.post_message(DataReceived('raw', reading()))
            await pilot.pause()
            await app.monitor._flush_writes()
            await pilot.pause()
            assert app.monitor.query_one(StatsWidget).recording_error == 'disk full'
            assert len(app.monitor.recorded_data) == 1
    asyncio.run(scenario())


def test_export_failure_keeps_app_open_for_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    real_open = open

    def fail_export(path, *args, **kwargs):
        if str(path).endswith('.csv'):
            raise OSError('export unavailable')
        return real_open(path, *args, **kwargs)

    async def scenario():
        app = OfflineApp(DatabaseHandler(str(tmp_path / 'data.sqlite')))
        async with app.run_test() as pilot:
            app.monitor.post_message(DataReceived('raw', reading()))
            await pilot.pause()
            with monkeypatch.context() as patch:
                patch.setattr('builtins.open', fail_export)
                worker = app.monitor.action_quit_app()
                await worker.wait()
                assert not app.monitor._quitting
                assert app.monitor.query_one(StatsWidget).device_status == 'STOPPED — SAVE FAILED'
                assert len(app.monitor.recorded_data) == 1
            await app.monitor.action_quit_app().wait()
        assert len(list(tmp_path.glob('egm4_data_*.csv'))) == 1
    asyncio.run(scenario())


def test_live_slope_uses_monotonic_time(monkeypatch):
    clock = iter([100, 105, 110])
    monkeypatch.setattr('src.tui.screens.monitor.time.monotonic', lambda: next(clock))
    monitor = MonitorScreen(None)
    assert monitor._update_slope(reading(None, 400, kind='M')) is None
    assert monitor._update_slope(reading(None, 410, kind='M')).slope == 2
    assert monitor._update_slope(reading(None, 800, plot=2, kind='M')) is None
    monitor._writer.shutdown()


def test_database_insert_errors_propagate(tmp_path):
    db = DatabaseHandler(str(tmp_path / 'data.sqlite'))
    with sqlite3.connect(db.db_path) as conn:
        conn.execute('DROP TABLE readings')
    with pytest.raises(sqlite3.OperationalError):
        db.insert_reading(1, reading())


def test_resume_preserves_measurements_and_notes(tmp_path):
    async def scenario():
        db = DatabaseHandler(str(tmp_path / 'data.sqlite'))
        session = db.create_session()
        db.insert_reading(session, reading(10, 410))
        db.insert_reading(session, dict(type='NOTE', plot=1, dt_s=10,
                                       co2_ppm=410, note='collar checked'))
        app = OfflineApp(db)
        app.monitor = MonitorScreen(None, db_handler=db, resume_session_id=session)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.monitor.recorded_data) == 2
            assert app.monitor.recorded_data[1]['note'] == 'collar checked'
            app.monitor.post_message(DataReceived('raw', reading(20, 420)))
            await pilot.pause()
            await app.monitor._flush_writes()
            assert len(db.get_session_readings(session)) == 3
    asyncio.run(scenario())


def test_quit_retains_in_flight_serial_read(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.chdir(tmp_path)

    class InFlightSerial:
        running = True
        data_callback = None
        error_callback = None

        async def connect(self, port):
            self.running = True
            return True

        async def process_loop(self):
            started.set()
            # Simulate a read already in progress when shutdown starts.
            await asyncio.sleep(0.05)
            self.data_callback('last record', reading(10, 450))

        async def disconnect(self):
            self.running = False

    async def scenario():
        nonlocal started
        started = asyncio.Event()
        db = DatabaseHandler(str(tmp_path / 'data.sqlite'))
        app = OfflineApp(db)
        async with app.run_test():
            monitor = app.monitor
            monitor.serial = InFlightSerial()
            monitor._serial_worker = monitor.start_serial_reading()
            await started.wait()
            await monitor.action_quit_app().wait()
        assert len(db.get_session_readings(monitor.session_id)) == 1
        with next(tmp_path.glob('egm4_data_*.csv')).open() as f:
            assert next(csv.DictReader(f))['co2_ppm'] == '450'

    started = None
    asyncio.run(scenario())
