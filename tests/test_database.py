import sqlite3

from src.database import DatabaseHandler


def test_database_preserves_export_metadata_and_events(tmp_path) -> None:
    db_path = tmp_path / "egm4.sqlite"
    db = DatabaseHandler(str(db_path))
    session_id = db.create_session(notes="field session")

    db.insert_reading(
        session_id,
        {
            "timestamp": "2026-01-18T13:17:00",
            "type": "R",
            "plot": 3,
            "record": 12,
            "day": 18,
            "month": 1,
            "hour": 13,
            "minute": 17,
            "co2_ppm": 429,
            "h2o": 5,
            "rht": 12.3,
            "temp": 8.4,
            "atmp": 965,
            "dc": 42,
            "dt": 30,
            "sr": 1.25,
            "probe_type": 8,
            "raw_line": "R030012180113170042900005001230000000000420030012500096508",
        },
    )
    db.insert_reading(
        session_id,
        {
            "timestamp": "2026-01-18T13:18:00",
            "type": "NOTE",
            "plot": 3,
            "record": 12,
            "co2_ppm": 431,
            "dt_s": 35,
            "note": "collar seated",
            "raw_line": "collar seated",
        },
    )
    db.insert_reading(
        session_id,
        {
            "timestamp": "2026-01-18T13:19:00",
            "type": "SAMPLE",
            "plot": 3,
            "co2_ppm": 710,
            "dt_s": 40,
            "sample_id": 1,
            "sample_label": "bag A",
            "sample_ppm": 710,
            "sample_peak_ppm": 780,
        },
    )

    rows = db.get_session_readings(session_id)

    assert rows[0]["record_type"] == "R"
    assert rows[0]["device_day"] == 18
    assert rows[0]["device_month"] == 1
    assert rows[0]["device_hour"] == 13
    assert rows[0]["device_minute"] == 17
    assert rows[0]["rht"] == 12.3
    assert rows[0]["raw_line"].startswith("R030012")

    assert rows[1]["record_type"] == "NOTE"
    assert rows[1]["note"] == "collar seated"
    assert rows[1]["elapsed_time"] == 35

    assert rows[2]["record_type"] == "SAMPLE"
    assert rows[2]["sample_id"] == "1"
    assert rows[2]["sample_label"] == "bag A"
    assert rows[2]["sample_ppm"] == 710
    assert rows[2]["sample_peak_ppm"] == 780

    db.end_session(session_id)
    conn = sqlite3.connect(db_path)
    end_time = conn.execute("SELECT end_time FROM sessions WHERE id = ?", (session_id,)).fetchone()[0]
    conn.close()
    assert end_time is not None
