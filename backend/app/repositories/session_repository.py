import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from backend.app.core.config import settings
from backend.app.data.shot_catalogue import resolve_shot_category
from backend.app.data.reference_catalogue import AUTHENTIC_REFERENCE_REGISTRY

logger = logging.getLogger(__name__)

class SessionRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or settings.DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    video_filename TEXT NOT NULL,
                    original_path TEXT,
                    annotated_path TEXT,
                    thumbnail_path TEXT,
                    shot_type TEXT DEFAULT 'Unknown',
                    predicted_shot_type TEXT DEFAULT 'Unknown',
                    prediction_confidence REAL DEFAULT 0.0,
                    user_confirmed_shot_type TEXT,
                    category TEXT DEFAULT 'Other',
                    handedness TEXT DEFAULT 'Right',
                    camera_angle TEXT DEFAULT 'Side View',
                    fps REAL DEFAULT 30.0,
                    duration_sec REAL DEFAULT 0.0,
                    total_frames INTEGER DEFAULT 0,
                    analyzed_frames INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'queued',
                    progress REAL DEFAULT 0.0,
                    current_step TEXT DEFAULT 'Initialized',
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result_json TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reference_videos (
                    id TEXT PRIMARY KEY,
                    shot_id TEXT NOT NULL,
                    shot_name TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    video_url TEXT NOT NULL,
                    thumbnail_url TEXT,
                    camera_view TEXT DEFAULT 'Side View',
                    verification_status TEXT DEFAULT 'verified',
                    description TEXT,
                    stance_setup TEXT,
                    footwork_weight_transfer TEXT,
                    body_positioning TEXT,
                    technique_points_json TEXT,
                    common_mistakes_json TEXT,
                    phases_json TEXT,
                    key_metrics_json TEXT,
                    is_custom_upload INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            # Safe non-destructive column migrations
            for col_sql in [
                "ALTER TABLE sessions ADD COLUMN category TEXT DEFAULT 'Other'",
                "ALTER TABLE sessions ADD COLUMN predicted_shot_type TEXT DEFAULT 'Unknown'",
                "ALTER TABLE sessions ADD COLUMN prediction_confidence REAL DEFAULT 0.0",
                "ALTER TABLE sessions ADD COLUMN user_confirmed_shot_type TEXT",
                "ALTER TABLE sessions ADD COLUMN striker_track_id INTEGER DEFAULT NULL",
                "ALTER TABLE sessions ADD COLUMN striker_tap_coords TEXT DEFAULT NULL",
                "ALTER TABLE sessions ADD COLUMN detected_camera_view TEXT DEFAULT 'side-on'",
                "ALTER TABLE sessions ADD COLUMN camera_view_warning TEXT DEFAULT NULL",
                "ALTER TABLE sessions ADD COLUMN shot_mismatch_warning TEXT DEFAULT NULL",
            ]:
                try:
                    conn.execute(col_sql)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass

            # Performance indexes on high-frequency query columns
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_shot_type ON sessions(shot_type)",
                "CREATE INDEX IF NOT EXISTS idx_ref_shot_name ON reference_videos(shot_name)",
            ]:
                try:
                    conn.execute(idx_sql)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass

        # Seed reference_videos if table is empty
        self._seed_reference_videos()

    def _seed_reference_videos(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM reference_videos WHERE is_custom_upload = 0")
            count = cur.fetchone()["cnt"]
            if count < len(AUTHENTIC_REFERENCE_REGISTRY):
                for ref in AUTHENTIC_REFERENCE_REGISTRY:
                    cur.execute("""
                        INSERT OR REPLACE INTO reference_videos (
                            id, shot_id, shot_name, player_name, source, source_url,
                            video_url, thumbnail_url, camera_view, verification_status,
                            description, stance_setup, footwork_weight_transfer,
                            body_positioning, technique_points_json, common_mistakes_json,
                            phases_json, key_metrics_json, is_custom_upload
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """, (
                        ref["id"],
                        ref["shot_id"],
                        ref["shot_name"],
                        ref["player_name"],
                        ref["source"],
                        ref.get("source_url", ""),
                        ref["video_url"],
                        ref.get("thumbnail_url", ""),
                        ref.get("camera_view", "Side View"),
                        ref.get("verification_status", "verified"),
                        ref.get("description", ""),
                        ref.get("stance_setup", ""),
                        ref.get("footwork_weight_transfer", ""),
                        ref.get("body_positioning", ""),
                        json.dumps(ref.get("technique_points", [])),
                        json.dumps(ref.get("common_mistakes", [])),
                        json.dumps(ref.get("phases", [])),
                        json.dumps(ref.get("key_metrics", {})),
                    ))
                conn.commit()

    def create_session(
        self,
        session_id: str,
        video_filename: str,
        original_path: str = "",
        shot_type: str = "Unknown",
        handedness: str = "Right",
        camera_angle: str = "Side View",
        category: Optional[str] = None,
        striker_track_id: Optional[int] = None,
        striker_tap_coords: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> Dict[str, Any]:
        if not category or category == "Other":
            category = resolve_shot_category(shot_type)
        with self._get_connection() as conn:
            if created_at:
                conn.execute("""
                    INSERT OR REPLACE INTO sessions (
                        session_id, video_filename, original_path, shot_type, predicted_shot_type,
                        prediction_confidence, category, handedness, camera_angle, striker_track_id, striker_tap_coords,
                        status, progress, current_step, created_at
                    ) VALUES (?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, 'queued', 0.0, 'File uploaded and queued for processing', ?)
                """, (session_id, video_filename, original_path, shot_type, shot_type, category, handedness, camera_angle, striker_track_id, striker_tap_coords, created_at))
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO sessions (
                        session_id, video_filename, original_path, shot_type, predicted_shot_type,
                        prediction_confidence, category, handedness, camera_angle, striker_track_id, striker_tap_coords,
                        status, progress, current_step
                    ) VALUES (?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, 'queued', 0.0, 'File uploaded and queued for processing')
                """, (session_id, video_filename, original_path, shot_type, shot_type, category, handedness, camera_angle, striker_track_id, striker_tap_coords))
            conn.commit()
        return self.get_session(session_id)

    def update_progress(self, session_id: str, status: str, progress: float, current_step: str, error: Optional[str] = None):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sessions
                SET status = ?, progress = ?, current_step = ?, error = ?
                WHERE session_id = ?
            """, (status, progress, current_step, error, session_id))
            conn.commit()

    def save_analysis_result(
        self,
        session_id: str,
        result_dict: Dict[str, Any],
        annotated_path: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        duration_sec: float = 0.0,
        total_frames: int = 0,
        analyzed_frames: int = 0,
        fps: float = 30.0,
        category: Optional[str] = None
    ):
        shot_type = result_dict.get("shot_type") or "Unknown"
        predicted_shot_type = result_dict.get("predicted_shot_type") or shot_type
        prediction_confidence = float(result_dict.get("prediction_confidence") or 0.0)
        user_confirmed_shot_type = result_dict.get("user_confirmed_shot_type")
        striker_track_id = result_dict.get("striker_track_id")
        detected_camera_view = result_dict.get("detected_camera_view", "side-on")
        camera_view_warning = result_dict.get("camera_view_warning")
        shot_mismatch_warning = result_dict.get("shot_mismatch_warning")
        resolved_category = category or resolve_shot_category(user_confirmed_shot_type or predicted_shot_type or shot_type)

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sessions
                SET status = 'completed',
                    progress = 100.0,
                    current_step = 'Analysis complete',
                    annotated_path = ?,
                    thumbnail_path = ?,
                    duration_sec = ?,
                    total_frames = ?,
                    analyzed_frames = ?,
                    fps = ?,
                    shot_type = ?,
                    predicted_shot_type = ?,
                    prediction_confidence = ?,
                    user_confirmed_shot_type = ?,
                    striker_track_id = ?,
                    detected_camera_view = ?,
                    camera_view_warning = ?,
                    shot_mismatch_warning = ?,
                    category = ?,
                    result_json = ?
                WHERE session_id = ?
            """, (
                annotated_path,
                thumbnail_path,
                duration_sec,
                total_frames,
                analyzed_frames,
                fps,
                shot_type,
                predicted_shot_type,
                prediction_confidence,
                user_confirmed_shot_type,
                striker_track_id,
                detected_camera_view,
                camera_view_warning,
                shot_mismatch_warning,
                resolved_category,
                json.dumps(result_dict),
                session_id
            ))
            conn.commit()

    def confirm_shot_type(self, session_id: str, confirmed_shot_type: str) -> Optional[Dict[str, Any]]:
        """Allows user to manually confirm or override the detected shot type."""
        resolved_category = resolve_shot_category(confirmed_shot_type)
        session = self.get_session(session_id)
        if not session:
            return None

        result_dict = session.get("result") or {}
        result_dict["shot_type"] = confirmed_shot_type
        result_dict["user_confirmed_shot_type"] = confirmed_shot_type
        result_dict["category"] = resolved_category

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sessions
                SET shot_type = ?,
                    user_confirmed_shot_type = ?,
                    category = ?,
                    result_json = ?
                WHERE session_id = ?
            """, (
                confirmed_shot_type,
                confirmed_shot_type,
                resolved_category,
                json.dumps(result_dict),
                session_id
            ))
            conn.commit()

        return self.get_session(session_id)

    def update_striker_track_id(self, session_id: str, track_id: int):
        """Updates striker_track_id and resets session status to queued for re-processing."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sessions
                SET striker_track_id = ?,
                    status = 'queued',
                    progress = 0.0,
                    current_step = 'Re-analyzing with selected striker...'
                WHERE session_id = ?
            """, (track_id, session_id))
            conn.commit()

    def update_result(self, session_id: str, result_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates result_json and associated columns for a session."""
        shot_type = result_dict.get("shot_type") or "Unknown"
        resolved_category = resolve_shot_category(shot_type)
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sessions
                SET shot_type = ?,
                    user_confirmed_shot_type = ?,
                    category = ?,
                    result_json = ?
                WHERE session_id = ?
            """, (
                shot_type,
                result_dict.get("user_confirmed_shot_type"),
                resolved_category,
                json.dumps(result_dict),
                session_id
            ))
            conn.commit()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            if not data.get("category") or data.get("category") == "Other":
                data["category"] = resolve_shot_category(data.get("shot_type", "Unknown"))
            if data.get("result_json"):
                try:
                    data["result"] = json.loads(data["result_json"])
                    if isinstance(data["result"], dict):
                        data["summary"] = data["result"].get("summary")
                        data["overall_technique_score"] = data["result"].get("overall_technique_score")
                        data["top_mistakes"] = data["result"].get("top_mistakes")
                except (json.JSONDecodeError, TypeError, ValueError) as json_err:
                    logger.warning(f"Error parsing result_json for session {data.get('session_id')}: {json_err}")
                    data["result"] = None
            else:
                data["result"] = None
            return data

    def list_sessions(
        self,
        limit: int = 50,
        shot_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM sessions WHERE 1=1"
            params: List[Any] = []

            if shot_type and shot_type.lower() != "all":
                query += " AND (LOWER(shot_type) = LOWER(?) OR LOWER(user_confirmed_shot_type) = LOWER(?))"
                params.extend([shot_type, shot_type])

            if category and category.lower() != "all":
                query += " AND LOWER(category) = LOWER(?)"
                params.append(category)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if not item.get("category") or item.get("category") == "Other":
                    item["category"] = resolve_shot_category(item.get("shot_type", "Unknown"))
                if item.get("result_json"):
                    try:
                        item["result"] = json.loads(item["result_json"])
                        if isinstance(item["result"], dict):
                            item["summary"] = item["result"].get("summary")
                            item["overall_technique_score"] = item["result"].get("overall_technique_score")
                            item["top_mistakes"] = item["result"].get("top_mistakes")
                    except (json.JSONDecodeError, TypeError, ValueError) as json_err:
                        logger.warning(f"Error parsing result_json for session in list: {json_err}")
                        item["result"] = None
                else:
                    item["result"] = None
                results.append(item)
            return results

    def delete_session(self, session_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Reference Video Management
    # -------------------------------------------------------------------------
    def get_reference_by_shot(self, shot_id_or_slug: str) -> Optional[Dict[str, Any]]:
        clean_raw = shot_id_or_slug.strip().lower()
        clean_space = clean_raw.replace("-", " ")
        clean_under = clean_raw.replace("-", "_")
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM reference_videos
                WHERE LOWER(shot_id) IN (?, ?, ?) OR LOWER(shot_name) IN (?, ?, ?)
                ORDER BY is_custom_upload DESC, created_at DESC LIMIT 1
            """, (clean_raw, clean_space, clean_under, clean_raw, clean_space, clean_under))
            row = cur.fetchone()
            if not row:
                # Fuzzy match
                cur.execute("""
                    SELECT * FROM reference_videos
                    WHERE LOWER(shot_id) LIKE ? OR LOWER(shot_name) LIKE ? OR LOWER(shot_id) LIKE ? OR LOWER(shot_name) LIKE ?
                    ORDER BY is_custom_upload DESC, created_at DESC LIMIT 1
                """, (f"%{clean_under}%", f"%{clean_space}%", f"%{clean_raw}%", f"%{clean_raw}%"))
                row = cur.fetchone()

            if not row:
                return None

            data = dict(row)
            data["technique_points"] = json.loads(data.get("technique_points_json") or "[]")
            data["common_mistakes"] = json.loads(data.get("common_mistakes_json") or "[]")
            data["phases"] = json.loads(data.get("phases_json") or "[]")
            data["key_metrics"] = json.loads(data.get("key_metrics_json") or "{}")
            return data

    def get_reference_by_id(self, ref_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM reference_videos WHERE id = ?", (ref_id,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            data["technique_points"] = json.loads(data.get("technique_points_json") or "[]")
            data["common_mistakes"] = json.loads(data.get("common_mistakes_json") or "[]")
            data["phases"] = json.loads(data.get("phases_json") or "[]")
            data["key_metrics"] = json.loads(data.get("key_metrics_json") or "{}")
            return data

    def list_all_references(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM reference_videos ORDER BY shot_name ASC")
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["technique_points"] = json.loads(item.get("technique_points_json") or "[]")
                item["common_mistakes"] = json.loads(item.get("common_mistakes_json") or "[]")
                item["phases"] = json.loads(item.get("phases_json") or "[]")
                item["key_metrics"] = json.loads(item.get("key_metrics_json") or "{}")
                results.append(item)
            return results

    def save_reference(self, ref_dict: Dict[str, Any]):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO reference_videos (
                    id, shot_id, shot_name, player_name, source, source_url,
                    video_url, thumbnail_url, camera_view, verification_status,
                    description, stance_setup, footwork_weight_transfer,
                    body_positioning, technique_points_json, common_mistakes_json,
                    phases_json, key_metrics_json, is_custom_upload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ref_dict["id"],
                ref_dict["shot_id"],
                ref_dict["shot_name"],
                ref_dict["player_name"],
                ref_dict["source"],
                ref_dict.get("source_url", ""),
                ref_dict["video_url"],
                ref_dict.get("thumbnail_url", ""),
                ref_dict.get("camera_view", "Side View"),
                ref_dict.get("verification_status", "verified"),
                ref_dict.get("description", ""),
                ref_dict.get("stance_setup", ""),
                ref_dict.get("footwork_weight_transfer", ""),
                ref_dict.get("body_positioning", ""),
                json.dumps(ref_dict.get("technique_points", [])),
                json.dumps(ref_dict.get("common_mistakes", [])),
                json.dumps(ref_dict.get("phases", [])),
                json.dumps(ref_dict.get("key_metrics", {})),
                1 if ref_dict.get("is_custom_upload") else 0
            ))
            conn.commit()

session_repo = SessionRepository()
