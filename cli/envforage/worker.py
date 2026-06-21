import sqlite3
import json
import time
import logging
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("TelemetryWorker")

class OfflineSyncQueue:
    """
    A thread-safe, SQLite-backed persistent queue for storing hardware telemetry
    when the agent is offline, allowing robust background synchronization.
    """
    def __init__(self, db_path: str = "~/.envforage/telemetry.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._lock = threading.Lock()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS telemetry_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    payload TEXT,
                    retry_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON telemetry_queue(status)')

    def enqueue(self, payload: Dict[str, Any]):
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO telemetry_queue (timestamp, payload) VALUES (?, ?)",
                    (time.time(), json.dumps(payload))
                )
                logger.debug("Enqueued new telemetry payload.")

    def fetch_batch(self, batch_size: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM telemetry_queue WHERE status = 'pending' AND retry_count < 5 ORDER BY timestamp ASC LIMIT ?",
                    (batch_size,)
                )
                return [dict(row) for row in cursor.fetchall()]

    def mark_success(self, item_ids: List[int]):
        if not item_ids:
            return
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                placeholders = ','.join(['?'] * len(item_ids))
                conn.execute(
                    f"UPDATE telemetry_queue SET status = 'synced' WHERE id IN ({placeholders})",
                    item_ids
                )

    def mark_failed(self, item_ids: List[int]):
        if not item_ids:
            return
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                placeholders = ','.join(['?'] * len(item_ids))
                conn.execute(
                    f"UPDATE telemetry_queue SET retry_count = retry_count + 1 WHERE id IN ({placeholders})",
                    item_ids
                )

class BackgroundSyncWorker:
    """Daemon thread worker that continuously attempts to sync the SQLite queue."""
    def __init__(self, endpoint_url: str):
        self.queue = OfflineSyncQueue()
        self.endpoint_url = endpoint_url
        self.is_running = False
        self._thread = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("Background sync worker started.")

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _is_online(self) -> bool:
        try:
            urllib.request.urlopen("http://8.8.8.8", timeout=1)
            return True
        except urllib.error.URLError:
            return False

    def _run_loop(self):
        while self.is_running:
            try:
                batch = self.queue.fetch_batch()
                if not batch:
                    time.sleep(10) # Idle sleep
                    continue

                if not self._is_online():
                    logger.debug("Offline. Postponing sync.")
                    time.sleep(30)
                    continue

                success_ids = []
                failed_ids = []

                # Simulate batch upload
                for item in batch:
                    try:
                        req = urllib.request.Request(
                            self.endpoint_url,
                            data=item['payload'].encode('utf-8'),
                            headers={'Content-Type': 'application/json'},
                            method='POST'
                        )
                        with urllib.request.urlopen(req, timeout=5):
                            success_ids.append(item['id'])
                    except Exception as e:
                        logger.warning(f"Failed to sync item {item['id']}: {e}")
                        failed_ids.append(item['id'])

                self.queue.mark_success(success_ids)
                self.queue.mark_failed(failed_ids)

            except Exception as e:
                logger.error(f"Worker loop encountered critical error: {e}")
                time.sleep(60) # Backoff on critical failure
