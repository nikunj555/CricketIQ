import os
import sys
import time
import logging
import threading
import urllib.request
from typing import Optional

logger = logging.getLogger("cricketiq.keepalive")


class KeepAliveService:
    """Lightweight background keep-alive pinger.
    
    Prevents free cloud hosting providers (e.g. Render free tier) from spinning down
    due to its default 15-minute HTTP inactivity timeout.
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.target_url: str = ""
        self.interval_sec: int = 540  # 9 minutes
        self.last_ping_time: Optional[float] = None
        self.last_status: Optional[str] = None
        self.total_pings: int = 0

    def start(self, target_url: Optional[str] = None, interval_sec: int = 540):
        # Auto-detect Render external URL or explicit KEEP_ALIVE_URL
        url = target_url or os.getenv("KEEP_ALIVE_URL") or os.getenv("RENDER_EXTERNAL_URL") or ""
        url = url.strip()
        if not url:
            # On local dev, do not run keep-alive
            logger.debug("No external keep-alive URL configured; skipping keep-alive service.")
            return

        # Normalize URL to /api/health
        url = url.rstrip("/")
        if not url.endswith("/api/health"):
            url = f"{url}/api/health"

        self.target_url = url
        self.interval_sec = max(60, interval_sec)
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="cricketiq-keepalive"
        )
        self._thread.start()
        logger.info(f"Keep-alive service active: target={self.target_url}, interval={self.interval_sec}s")

    def stop(self):
        self._stop_event.set()

    def _run_loop(self):
        # Wait 45 seconds after process start so application fully binds and warms up
        if self._stop_event.wait(45):
            return

        while not self._stop_event.is_set():
            self._ping()
            if self._stop_event.wait(self.interval_sec):
                break

    def _ping(self):
        try:
            req = urllib.request.Request(
                self.target_url,
                headers={"User-Agent": "CricketIQ-Internal-KeepAlive/1.0"}
            )
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=30) as resp:
                elapsed = round(time.time() - t0, 2)
                self.last_ping_time = time.time()
                self.last_status = f"HTTP {resp.status} in {elapsed}s"
                self.total_pings += 1
                logger.info(f"Keep-alive ping #{self.total_pings} successful: {self.target_url} -> {self.last_status}")
        except Exception as e:
            self.last_status = f"Error: {e}"
            logger.warning(f"Keep-alive ping notice for {self.target_url}: {e}")

    def get_status(self) -> dict:
        return {
            "active": self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set(),
            "target_url": self.target_url,
            "interval_sec": self.interval_sec,
            "last_ping_time": self.last_ping_time,
            "last_status": self.last_status,
            "total_pings": self.total_pings,
        }


keepalive_service = KeepAliveService()
