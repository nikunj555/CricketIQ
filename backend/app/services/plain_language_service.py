"""
CricketIQ — Plain-English Coaching Feedback Engine
Transforms raw joint measurements into human, friendly coaching feedback:
  - Spoken like an experienced coach at the nets: average sentence < 15 words.
  - Strict zero-jargon rule in the default layer (no flexion, torso, DTW, tolerance).
  - One-line verdict + technique score label + ONE single focus for the next 10 balls.
  - Top 3 issue cards: Title (<= 8 words), Where & When, Why it matters (1 sentence),
    How to fix it (feel cue, 1 sentence), One drill (name + 2 lines), Severity in words.
  - Collapsible "Show proof" layer retaining exact measured numbers and sparklines.
  - Multi-language support: English and Hindi/Hinglish (spoken academy style).
"""

import re
import yaml
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

BANNED_WORDS = {
    "flexion",
    "extension",
    "kinematic",
    "kinetic",
    "deviation",
    "tolerance",
    "trajectory",
    "torso",
    "lateral",
    "medial",
    "dtw",
    "landmark",
    "trigger movement",
    "lead knee",
    "rear knee",
    "lead elbow",
    "rear elbow"
}


class PlainLanguageService:
    """Plain-English Coaching Feedback Engine."""

    def __init__(self):
        self._data_dir = Path(__file__).resolve().parent.parent / "data"
        self._vocab_en: Dict[str, Any] = {}
        self._vocab_hi: Dict[str, Any] = {}
        self._load_vocabularies()

    def _load_vocabularies(self):
        en_path = self._data_dir / "plain_language.yaml"
        hi_path = self._data_dir / "plain_language.hi.yaml"

        if en_path.exists():
            with open(en_path, "r", encoding="utf-8") as f:
                self._vocab_en = yaml.safe_load(f) or {}

        if hi_path.exists():
            with open(hi_path, "r", encoding="utf-8") as f:
                self._vocab_hi = yaml.safe_load(f) or {}

    def get_vocab(self, lang: str = "en") -> Dict[str, Any]:
        """Returns the dictionary for the requested language with English fallback."""
        if lang.lower().startswith("hi"):
            return self._vocab_hi or self._vocab_en
        return self._vocab_en

    def _translate_phase(self, phase_name: str, lang: str = "en") -> str:
        vocab = self.get_vocab(lang)
        timing_map = vocab.get("timing_phases", {})
        p_clean = phase_name.lower().strip()
        for k, v in timing_map.items():
            if k in p_clean:
                return v
        return "at the moment of hitting the ball"

    def _translate_body_part(self, metric_key: str, lang: str = "en") -> str:
        vocab = self.get_vocab(lang)
        parts = vocab.get("body_parts", {})
        if "lead_knee" in metric_key:
            return parts.get("lead_knee", "front knee")
        if "rear_knee" in metric_key:
            return parts.get("rear_knee", "back knee")
        if "lead_elbow" in metric_key:
            return parts.get("lead_elbow", "front elbow")
        if "rear_elbow" in metric_key:
            return parts.get("rear_elbow", "back elbow")
        if "torso" in metric_key:
            return parts.get("torso_lean", "upper body")
        if "head" in metric_key:
            return parts.get("head_position", "head")
        if "stance" in metric_key:
            return parts.get("stance_width", "front step")
        return "body"

    def get_score_label(self, score: float, lang: str = "en") -> Tuple[str, str]:
        """Returns the score category label and code."""
        vocab = self.get_vocab(lang)
        labels = vocab.get("technique_score_labels", {})
        if score >= 85.0:
            return labels.get("excellent", "Excellent"), "excellent"
        if score >= 70.0:
            return labels.get("good", "Good"), "good"
        if score >= 50.0:
            return labels.get("getting_there", "Getting there"), "getting_there"
        return labels.get("needs_work", "Needs work"), "needs_work"

    def compose_issue_card(
        self,
        metric_key: str,
        measured_val: float,
        min_ideal: float,
        max_ideal: float,
        phase: str,
        shot_name: str,
        frame_index: Optional[int],
        timestamp_sec: Optional[float],
        confidence: float,
        severity_rank: int,
        time_series: List[Dict[str, Any]],
        lang: str = "en"
    ) -> Dict[str, Any]:
        """Composes a complete 6-part plain-English Issue Card."""
        vocab = self.get_vocab(lang)
        en_vocab = self._vocab_en
        metric_entry = vocab.get("metrics", {}).get(metric_key) or en_vocab.get("metrics", {}).get(metric_key, {})

        is_too_high = measured_val > max_ideal
        sub_key = "too_high" if is_too_high else "too_low"
        info = metric_entry.get(sub_key) or en_vocab.get("metrics", {}).get(metric_key, {}).get(sub_key, {})

        # Where and when
        timing_str = self._translate_phase(phase, lang)
        where_and_when = f"{timing_str.capitalize()}"
        if timestamp_sec is not None:
            where_and_when += f" ({timestamp_sec:.2f}s)"

        # Title (ensure <= 8 words)
        title = info.get("title", f"Check your {self._translate_body_part(metric_key, lang)}")
        title_words = title.split()
        if len(title_words) > 8:
            title = " ".join(title_words[:8])

        # Why it matters (1 sentence)
        why = info.get("why", "This affects your balance and control through the stroke.")

        # How to fix it (feel cue, 1 sentence; check for shot-specific variant)
        shot_lower = shot_name.lower()
        if "sweep" in shot_lower and info.get("feel_cue_sweep"):
            feel_cue = info["feel_cue_sweep"]
        elif "pull" in shot_lower and info.get("feel_cue_pull"):
            feel_cue = info["feel_cue_pull"]
        elif "defensive" in shot_lower and info.get("feel_cue_defensive"):
            feel_cue = info["feel_cue_defensive"]
        else:
            feel_cue = info.get("feel_cue", "Keep your front knee bent and your eyes level as you play.")

        # Drill (name + 2 steps)
        drill_name = info.get("drill_name", "Shadow Balance Drill")
        drill_steps = info.get("drill_steps", "Play your stroke in slow motion. Hold the finish for two seconds. 10 reps.")

        # Severity in plain words
        sev_map = vocab.get("severity_levels", {})
        if severity_rank == 0:
            severity_label = sev_map.get("high", "Fix this first")
            severity_code = "high"
            severity_color = "red"
        elif severity_rank == 1:
            severity_label = sev_map.get("medium", "Worth improving")
            severity_code = "medium"
            severity_color = "amber"
        else:
            severity_label = sev_map.get("low", "Minor")
            severity_code = "low"
            severity_color = "grey"

        # Time-series sparkline for the technical proof layer
        sparkline = []
        for f in time_series:
            val = f.get(metric_key)
            if val is not None:
                sparkline.append(round(float(val), 1))

        # Proof layer
        proof = {
            "technical_metric_name": metric_key,
            "measured_value": round(float(measured_val), 1),
            "ideal_min": round(float(min_ideal), 1),
            "ideal_max": round(float(max_ideal), 1),
            "unit": "°" if "angle" in metric_key or "lean" in metric_key else "x",
            "frame_index": frame_index,
            "timestamp_sec": round(float(timestamp_sec or 0.0), 2),
            "measurement_confidence": round(float(confidence), 2),
            "sparkline": sparkline[:30]
        }

        # Moment loop clip frame bounds (2-3 seconds = ~60-90 frames)
        target_f = frame_index or (len(time_series) // 2)
        loop_start_frame = max(0, target_f - 30)
        loop_end_frame = min(len(time_series) - 1, target_f + 40)

        # Highlighted body part for visual fix
        highlight_joint = "lead_knee"
        if "elbow" in metric_key:
            highlight_joint = "lead_elbow"
        elif "torso" in metric_key:
            highlight_joint = "torso"
        elif "head" in metric_key:
            highlight_joint = "head"
        elif "stance" in metric_key:
            highlight_joint = "lead_foot"

        return {
            "id": f"card_{metric_key}_{phase.lower()}",
            "title": title,
            "where_and_when": where_and_when,
            "why_it_matters": why,
            "how_to_fix": feel_cue,
            "feel_cue": feel_cue,
            "drill": {
                "name": drill_name,
                "instructions": drill_steps
            },
            "severity_label": severity_label,
            "severity_code": severity_code,
            "severity_color": severity_color,
            "target_body_part": self._translate_body_part(metric_key, lang),
            "highlight_joint": highlight_joint,
            "loop_window": {
                "center_frame": target_f,
                "start_frame": loop_start_frame,
                "end_frame": loop_end_frame,
                "timestamp_sec": timestamp_sec
            },
            "proof": proof
        }

    def compose_top_summary(
        self,
        shot_name: str,
        technique_score: float,
        issue_cards: List[Dict[str, Any]],
        measured_strengths: List[Dict[str, Any]],
        unmeasurable_items: List[str],
        lang: str = "en"
    ) -> Dict[str, Any]:
        """Composes B1 Top Summary."""
        vocab = self.get_vocab(lang)
        score_label, score_code = self.get_score_label(technique_score, lang)

        # ONE focus for the next 10 balls (matches top issue)
        one_focus = None
        focus_body_part = "balance"
        if issue_cards:
            top_issue = issue_cards[0]
            focus_body_part = top_issue["target_body_part"]
            one_focus = {
                "title": f"Focus on your {top_issue['target_body_part']}",
                "cue": top_issue["how_to_fix"],
                "target_body_part": top_issue["target_body_part"],
                "source_issue_id": top_issue["id"]
            }

        # One-line verdict
        verdicts = vocab.get("overall_verdicts", {})
        template = verdicts.get(score_code, "Good {shot_name}. Focus on your {focus_body_part}.")
        one_line_verdict = template.format(shot_name=shot_name, focus_body_part=focus_body_part)

        # What you did well (1-2 specific strengths)
        strengths_list = []
        vocab_strengths = vocab.get("strengths", {})
        for st in measured_strengths[:2]:
            st_key = st.get("key", "balanced_base")
            st_info = vocab_strengths.get(st_key, vocab_strengths.get("balanced_base", {}))
            strengths_list.append({
                "title": st_info.get("title", st.get("title", "Solid balance")),
                "sentence": st_info.get("sentence", "Your balance was solid through the shot.")
            })

        if not strengths_list and technique_score >= 70:
            strengths_list.append({
                "title": "Solid, balanced foundation",
                "sentence": "Your feet and upper body remained stable right through contact."
            })

        # Unmeasurable notices
        unmeasurable_notices = []
        notices_templates = vocab.get("unmeasurable_notices", {})
        for item in unmeasurable_items:
            if isinstance(item, dict):
                notice_type = item.get("type", "out_of_frame")
                body_part = item.get("body_part", "body")
                t = notices_templates.get(notice_type, notices_templates.get("out_of_frame"))
                unmeasurable_notices.append(t.format(body_part=body_part))
            elif str(item) in notices_templates:
                unmeasurable_notices.append(notices_templates[str(item)])
            elif "front knee" in str(item).lower() or "knee" in str(item).lower():
                unmeasurable_notices.append(notices_templates.get("camera_view_knee", "We couldn't check your front knee from this angle. For knee advice, film from side-on (square with the pitch)."))
            else:
                t = notices_templates.get("out_of_frame", "We couldn't check your {body_part} because it was out of frame. Film from the side with your whole body visible.")
                unmeasurable_notices.append(t.format(body_part=item))

        return {
            "one_line_verdict": one_line_verdict,
            "technique_score": round(float(technique_score), 1),
            "score_label": score_label,
            "score_code": score_code,
            "one_focus_for_next_10_balls": one_focus,
            "what_you_did_well": strengths_list,
            "unmeasurable_notices": unmeasurable_notices
        }

    @staticmethod
    def lint_text_for_banned_jargon(text: str) -> List[str]:
        """
        Enforces language rules: returns any occurrences of banned jargon in default-layer text.
        """
        found = []
        lower_t = text.lower()
        for word in BANNED_WORDS:
            # Match word boundary
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, lower_t):
                found.append(word)
        return found

    @staticmethod
    def calculate_average_sentence_length(text: str) -> float:
        """Computes the average word count per sentence in a block of text."""
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if not sentences:
            return 0.0
        word_counts = [len(s.split()) for s in sentences]
        return float(np.mean(word_counts))


plain_language_service = PlainLanguageService()
