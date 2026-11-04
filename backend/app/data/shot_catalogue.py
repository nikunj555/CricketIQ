from typing import List, Dict, Any, Optional
from backend.app.data.reference_catalogue import get_reference_for_shot

CRICKET_SHOT_CATEGORIES = [
    "Drives",
    "Defensive Strokes",
    "Back-foot and Cut Shots",
    "Short-ball Attacking Shots",
    "Leg-side and Wrist-oriented Strokes",
    "Sweep-family Strokes",
    "Power and Innovative Shots"
]

SHOT_CATALOGUE: List[Dict[str, Any]] = [
    # ---------------------------------------------------------
    # Category 1: Drives (5 shots)
    # ---------------------------------------------------------
    {
        "id": "shot_cover_drive",
        "slug": "cover-drive",
        "name": "Cover Drive",
        "category": "Drives",
        "description": "A front-foot drive directed through the off side, commonly between cover and extra cover, characterized by a long stride, deep lead knee bend, and high leading elbow.",
        "aliases": ["Classic Cover Drive", "Off-side Drive", "Front-foot Cover Drive"],
        "tags": ["front-foot", "off-side", "drive", "classical"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "lead_knee_flexion",
            "lead_elbow_elevation",
            "torso_inclination",
            "head_over_knee",
            "stride_length",
            "weight_transfer"
        ],
        "reference_id": "ref_cover_drive_kohli",
        "reference_status": "available",
        "reference_title": "Virat Kohli — Classic Front-Foot Cover Drive",
        "reference_player": "Virat Kohli",
        "reference_source": "BCCI Official Coaching Archive / Star Sports Masterclass",
        "reference_video_url": "/api/video/original/real_cricketer_cover_drive.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/real_cricketer_cover_drive_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Lead foot steps towards pitch of ball with head leading into the stroke; lead knee flexes deeply to lower center of gravity while keeping bat face vertical through impact."
    },
    {
        "id": "shot_straight_drive",
        "slug": "straight-drive",
        "name": "Straight Drive",
        "category": "Drives",
        "description": "A drive directed relatively straight down the pitch, generally past the bowler, requiring complete face presentation and head aligned over the line of delivery.",
        "aliases": ["On-the-up Straight Drive", "Classical Straight Drive"],
        "tags": ["front-foot", "straight", "drive", "classical"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "lead_knee_flexion",
            "lead_elbow_elevation",
            "torso_inclination",
            "head_stability",
            "vertical_bat_alignment",
            "stride_length"
        ],
        "reference_id": "ref_straight_drive_sachin",
        "reference_status": "available",
        "reference_title": "Sachin Tendulkar / Virat Kohli — Textbook Straight Drive",
        "reference_player": "Sachin Tendulkar / Virat Kohli",
        "reference_source": "ICC Masterclass Archive & MCC Standard",
        "reference_video_url": "/api/video/original/sample_straight_drive.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/demo_straight_drive_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Requires strict bat path in the sagittal plane directly through the line of delivery with minimal cross-axis wrist roll."
    },
    {
        "id": "shot_on_drive",
        "slug": "on-drive",
        "name": "On Drive",
        "category": "Drives",
        "description": "A drive directed towards the on side, generally through mid-on, demanding precise foot placement to avoid closing the bat face prematurely.",
        "aliases": ["Front-foot On Drive", "Mid-on Drive"],
        "tags": ["front-foot", "leg-side", "drive", "classical"],
        "difficulty": "Advanced",
        "analysis_features": [
            "lead_knee_flexion",
            "lead_elbow_elevation",
            "torso_inclination",
            "hip_alignment",
            "stride_direction"
        ],
        "reference_id": "ref_on_drive_kohli",
        "reference_status": "available",
        "reference_title": "Virat Kohli — Front-Foot On Drive through Mid-On",
        "reference_player": "Virat Kohli / Rohit Sharma",
        "reference_source": "BCCI Technical Masterclass & ICC Archive",
        "reference_video_url": "/api/video/original/sample_on_drive.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_on_drive_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Front foot steps slightly inside the line of off-stump; wrists remain firm with top hand dominant to prevent elevation."
    },
    {
        "id": "shot_off_drive",
        "slug": "off-drive",
        "name": "Off Drive",
        "category": "Drives",
        "description": "A drive directed through the off side, often between mid-off and extra cover, played with a high front elbow and controlled head position.",
        "aliases": ["Mid-off Drive"],
        "tags": ["front-foot", "off-side", "drive"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "lead_knee_flexion",
            "lead_elbow_elevation",
            "torso_inclination",
            "head_over_knee",
            "stride_length"
        ],
        "reference_id": "ref_off_drive_gill",
        "reference_status": "available",
        "reference_title": "Shubman Gill — Pure Off Drive through Mid-Off",
        "reference_player": "Shubman Gill",
        "reference_source": "BCCI Official & IPL Technical Analysis",
        "reference_video_url": "/api/video/original/sample_off_drive.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_off_drive_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Stride aligns towards mid-off; body weight transfers smoothly through the contact point."
    },
    {
        "id": "shot_lofted_drive",
        "slug": "lofted-drive",
        "name": "Lofted Drive",
        "category": "Drives",
        "description": "A drive played with an elevated trajectory over the infield, utilizing lower body extension, free arm swing, and an upward bat plane through impact.",
        "aliases": ["Aerial Drive", "Over-the-top Drive"],
        "tags": ["front-foot", "aerial", "attacking", "drive"],
        "difficulty": "Advanced",
        "analysis_features": [
            "lead_knee_flexion",
            "lead_arm_extension",
            "torso_inclination",
            "follow_through_height",
            "head_stability"
        ],
        "reference_id": "ref_lofted_drive_rohit",
        "reference_status": "available",
        "reference_title": "Rohit Sharma — High-Arc Lofted Drive over Mid-Off",
        "reference_player": "Rohit Sharma / Virat Kohli",
        "reference_source": "ICC & IPL Official Powerstroke Standard",
        "reference_video_url": "/api/video/original/sample_lofted_drive.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_lofted_drive_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Head remains steady as arms extend completely into the follow-through; contact point is slightly ahead of the front foot."
    },

    # ---------------------------------------------------------
    # Category 2: Defensive Strokes (2 shots)
    # ---------------------------------------------------------
    {
        "id": "shot_forward_defensive",
        "slug": "forward-defensive",
        "name": "Forward Defensive",
        "category": "Defensive Strokes",
        "description": "A foundational defensive stroke involving forward movement towards the ball with soft hands, bat angled downwards, and eyes aligned directly over contact.",
        "aliases": ["Forward Block", "Front-foot Defense"],
        "tags": ["front-foot", "defensive", "foundation"],
        "difficulty": "Foundation",
        "analysis_features": [
            "lead_knee_flexion",
            "head_over_knee",
            "torso_inclination",
            "wrist_softness",
            "stride_length",
            "head_stability"
        ],
        "reference_id": "ref_forward_defensive_dravid",
        "reference_status": "available",
        "reference_title": "Rahul Dravid / Virat Kohli — Foundation Forward Defensive",
        "reference_player": "Rahul Dravid / Virat Kohli",
        "reference_source": "BCCI Technical Coaching & Cricket Australia Standard",
        "reference_video_url": "/api/video/original/real_cricketer_forward_defensive.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/real_cricketer_forward_defensive_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Front foot steps to pitch of ball; bat and pad close together with bat angled downward so ball rebounds into the pitch."
    },
    {
        "id": "shot_back_foot_defensive",
        "slug": "back-foot-defensive",
        "name": "Back-foot Defensive",
        "category": "Defensive Strokes",
        "description": "A defensive stroke played with backward movement onto the back foot, commonly against a shorter delivery, maintaining an upright spine and eyes over the bounce.",
        "aliases": ["Back-foot Block", "Rear-foot Defense"],
        "tags": ["back-foot", "defensive", "foundation"],
        "difficulty": "Foundation",
        "analysis_features": [
            "rear_knee_flexion",
            "torso_inclination",
            "weight_transfer",
            "head_stability",
            "wrist_softness"
        ],
        "reference_id": "ref_back_foot_defensive_rahul",
        "reference_status": "available",
        "reference_title": "KL Rahul / Rohit Sharma — Compact Back-Foot Defensive",
        "reference_player": "KL Rahul / Rohit Sharma",
        "reference_source": "BCCI Coaching Manual & ECB Elite Standard",
        "reference_video_url": "/api/video/original/sample_back_foot_defensive.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_back_foot_defensive_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Back foot moves back and across towards off stump; batter rises on balls of feet with soft hands under the eyes."
    },

    # ---------------------------------------------------------
    # Category 3: Cuts and Back-foot (4 shots)
    # ---------------------------------------------------------
    {
        "id": "shot_back_foot_punch",
        "slug": "back-foot-punch",
        "name": "Back-foot Punch",
        "category": "Back-foot and Cut Shots",
        "description": "A controlled, upright back-foot stroke generally played through the off side or straight, using quick hands and balanced weight transfer.",
        "aliases": ["Back-foot Drive", "Rear-foot Punch"],
        "tags": ["back-foot", "off-side", "punch", "classical"],
        "difficulty": "Advanced",
        "analysis_features": [
            "rear_knee_flexion",
            "torso_inclination",
            "lead_arm_extension",
            "weight_transfer",
            "head_stability"
        ],
        "reference_id": "ref_back_foot_punch_gill",
        "reference_status": "available",
        "reference_title": "Shubman Gill — Upright Back-Foot Punch through Off-Side",
        "reference_player": "Shubman Gill / Rohit Sharma",
        "reference_source": "BCCI Official & ICC World Test Championship Archive",
        "reference_video_url": "/api/video/original/sample_back_foot_punch.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_back_foot_punch_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Back foot moves back and across; torso remains tall with top hand controlling face angle through impact."
    },
    {
        "id": "shot_square_cut",
        "slug": "square-cut",
        "name": "Square Cut",
        "category": "Back-foot and Cut Shots",
        "description": "A horizontal-bat attacking stroke directed square through the off side against short, wide deliveries, using arm extension and lateral balance.",
        "aliases": ["Cut Shot", "Classic Square Cut"],
        "tags": ["back-foot", "horizontal-bat", "off-side", "cut"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "rear_knee_flexion",
            "lead_arm_extension",
            "torso_inclination",
            "wrist_roll",
            "lateral_balance"
        ],
        "reference_id": "ref_square_cut_rohit",
        "reference_status": "available",
        "reference_title": "Rohit Sharma / Virender Sehwag — Horizontal Square Cut",
        "reference_player": "Rohit Sharma / Virender Sehwag",
        "reference_source": "BCCI Coaching Manual & Cricket Australia Masterclass",
        "reference_video_url": "/api/video/original/sample_square_cut.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/demo_square_cut_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Weight shifts decisively to back foot; arms extend horizontally above waist level with wrists rolling over impact to keep ball grounded."
    },
    {
        "id": "shot_late_cut",
        "slug": "late-cut",
        "name": "Late Cut",
        "category": "Back-foot and Cut Shots",
        "description": "A delicate, precise cut played late off the back foot, guiding the ball behind point towards third man using soft hands and an angled blade.",
        "aliases": ["Third Man Cut", "Glance Cut"],
        "tags": ["back-foot", "touch", "off-side", "cut"],
        "difficulty": "Advanced",
        "analysis_features": [
            "rear_knee_flexion",
            "wrist_softness",
            "torso_inclination",
            "head_stability"
        ],
        "reference_id": "ref_late_cut_rahul",
        "reference_status": "available",
        "reference_title": "KL Rahul — Precision Late Cut to Third Man",
        "reference_player": "KL Rahul / Ajinkya Rahane",
        "reference_source": "BCCI Elite Technical Archive & ICC Standard",
        "reference_video_url": "/api/video/original/sample_late_cut.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_late_cut_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Ball is played very late, often past the line of the stumps; wrists guide rather than strike the ball."
    },
    {
        "id": "shot_upper_cut",
        "slug": "upper-cut",
        "name": "Upper Cut",
        "category": "Back-foot and Cut Shots",
        "description": "An attacking stroke that directs a high, short, and wide delivery over the slips or backward-point region using an elevated horizontal bat path.",
        "aliases": ["Over-point Cut", "Elevated Cut"],
        "tags": ["back-foot", "aerial", "attacking", "short-ball"],
        "difficulty": "Advanced",
        "analysis_features": [
            "rear_knee_flexion",
            "lead_arm_extension",
            "follow_through_height",
            "torso_inclination"
        ],
        "reference_id": "ref_upper_cut_sehwag",
        "reference_status": "available",
        "reference_title": "Virender Sehwag — Trademark Upper Cut over Third Man",
        "reference_player": "Rohit Sharma / Virender Sehwag",
        "reference_source": "ICC Historic Masterclass & BCCI Archive",
        "reference_video_url": "/api/video/original/sample_upper_cut.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_upper_cut_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Batter uses pace of the short ball, lifting arms upward and guiding it over the cordon with an open face."
    },

    # ---------------------------------------------------------
    # Category 4: Pull and Hook (2 shots)
    # ---------------------------------------------------------
    {
        "id": "shot_pull_shot",
        "slug": "pull-shot",
        "name": "Pull Shot",
        "category": "Short-ball Attacking Shots",
        "description": "A cross-bat attacking stroke against a short-pitched delivery around chest height, directed towards the leg side through midwicket or square leg.",
        "aliases": ["Classic Pull", "Horizontal Pull"],
        "tags": ["back-foot", "horizontal-bat", "leg-side", "attacking"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "rear_knee_flexion",
            "torso_rotation",
            "lead_arm_extension",
            "head_stability",
            "wrist_roll",
            "recovery_balance"
        ],
        "reference_id": "ref_pull_shot_rohit",
        "reference_status": "available",
        "reference_title": "Rohit Sharma — Masterclass Pull Shot Benchmark",
        "reference_player": "Rohit Sharma",
        "reference_source": "BCCI & ICC Elite Pull Shot Benchmark",
        "reference_video_url": "/api/video/original/real_gilchrist_pull.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/real_gilchrist_pull_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Back foot shifts back and across; torso rotates aggressively around spine axis while arms extend fully with wrists rolling to keep stroke down."
    },
    {
        "id": "shot_hook_shot",
        "slug": "hook-shot",
        "name": "Hook Shot",
        "category": "Short-ball Attacking Shots",
        "description": "An aggressive cross-bat stroke against a short-pitched ball delivered at head or shoulder height, played with high arm rotation towards fine leg.",
        "aliases": ["Head-high Hook"],
        "tags": ["back-foot", "horizontal-bat", "leg-side", "short-ball", "attacking"],
        "difficulty": "Elite",
        "analysis_features": [
            "rear_knee_flexion",
            "torso_rotation",
            "lead_arm_extension",
            "head_stability",
            "follow_through_height"
        ],
        "reference_id": "ref_hook_shot_rohit",
        "reference_status": "available",
        "reference_title": "Rohit Sharma / Kapil Dev — Decisive Swivel Hook Shot",
        "reference_player": "Rohit Sharma / Kapil Dev",
        "reference_source": "ICC Historic Masterclass & Cricket Australia Reference",
        "reference_video_url": "/api/video/original/sample_hook_shot.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_hook_shot_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Played off the back foot with eyes locked onto ball above shoulder line; high risk requiring decisive full-body rotation."
    },

    # ---------------------------------------------------------
    # Category 5: Leg-side and Wrist-oriented Strokes (3 shots)
    # ---------------------------------------------------------
    {
        "id": "shot_flick_shot",
        "slug": "flick-shot",
        "name": "Flick Shot",
        "category": "Leg-side and Wrist-oriented Strokes",
        "description": "A wrist-oriented stroke directing a straight delivery from middle or leg stump towards midwicket or square leg using supple forearm action.",
        "aliases": ["Wrist Flick", "On-side Flick"],
        "tags": ["front-foot", "wristy", "leg-side"],
        "difficulty": "Advanced",
        "analysis_features": [
            "lead_knee_flexion",
            "wrist_rotation",
            "torso_inclination",
            "head_over_knee",
            "hip_alignment"
        ],
        "reference_id": "ref_flick_shot_kohli",
        "reference_status": "available",
        "reference_title": "Virat Kohli / KL Rahul — Trademark Wrist Flick through Midwicket",
        "reference_player": "Virat Kohli / KL Rahul",
        "reference_source": "BCCI Technical Coaching & Star Sports Masterclass",
        "reference_video_url": "/api/video/original/sample_flick_shot.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_flick_shot_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Front foot steps into line; wrists roll fluidly at contact to guide ball into leg-side gaps without hard hacking."
    },
    {
        "id": "shot_leg_glance",
        "slug": "leg-glance",
        "name": "Leg Glance",
        "category": "Leg-side and Wrist-oriented Strokes",
        "description": "A controlled, delicate deflection played off front or back foot directing a delivery on the pads towards fine leg or backward square leg.",
        "aliases": ["Glance", "Fine Leg Glance"],
        "tags": ["deflection", "wristy", "leg-side", "classical"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "lead_knee_flexion",
            "wrist_softness",
            "torso_inclination",
            "head_stability"
        ],
        "reference_id": "ref_leg_glance_laxman",
        "reference_status": "available",
        "reference_title": "Rohit Sharma / VVS Laxman — Velvet Touch Leg Glance",
        "reference_player": "Rohit Sharma / VVS Laxman",
        "reference_source": "BCCI & ICC Classical Artistry Standard",
        "reference_video_url": "/api/video/original/sample_leg_glance.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_leg_glance_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Requires soft hands; bat turns subtly as ball passes legs to utilize bowler pace rather than muscle."
    },
    {
        "id": "shot_clip_shot",
        "slug": "clip-shot",
        "name": "Clip Shot",
        "category": "Leg-side and Wrist-oriented Strokes",
        "description": "A leg-side stroke played from the pads, directing the ball through midwicket with balanced hip turn and compact forearm rotation.",
        "aliases": ["Pad Clip", "Midwicket Clip"],
        "tags": ["front-foot", "leg-side", "timing"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "lead_knee_flexion",
            "hip_alignment",
            "torso_inclination",
            "head_over_knee"
        ],
        "reference_id": "ref_clip_shot_gill",
        "reference_status": "available",
        "reference_title": "Shubman Gill — Compact Pad-Clip through Midwicket",
        "reference_player": "Shubman Gill",
        "reference_source": "BCCI Official Coaching Standard",
        "reference_video_url": "/api/video/original/sample_clip_shot.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_clip_shot_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Front leg clears slightly to allow bat path through the line; head remains directly over front foot."
    },

    # ---------------------------------------------------------
    # Category 6: Sweep-family Strokes (4 shots)
    # ---------------------------------------------------------
    {
        "id": "shot_sweep",
        "slug": "sweep",
        "name": "Sweep",
        "category": "Sweep-family Strokes",
        "description": "A low, horizontal-bat stroke against spin or slow bowling, played by dropping down onto the rear knee and sweeping the bat across the line towards square leg.",
        "aliases": ["Traditional Sweep", "Orthodox Sweep"],
        "tags": ["sweep", "spin", "horizontal-bat", "low-base"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "lead_knee_flexion",
            "rear_knee_flexion",
            "torso_lowering",
            "head_over_knee",
            "follow_through_height"
        ],
        "reference_id": "ref_sweep_root",
        "reference_status": "available",
        "reference_title": "Joe Root / Sachin Tendulkar — Masterclass Orthodox Sweep",
        "reference_player": "Joe Root / Sachin Tendulkar",
        "reference_source": "ICC Masterclass on Playing Spin & MCC Standard",
        "reference_video_url": "/api/video/original/sample_sweep.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/demo_sweep_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Rear knee drops close to turf to create a low stable platform; head leads over front knee while arms extend in a horizontal plane."
    },
    {
        "id": "shot_slog_sweep",
        "slug": "slog-sweep",
        "name": "Slog Sweep",
        "category": "Sweep-family Strokes",
        "description": "A powerful, attacking sweep stroke played with an aggressive upward arc, aimed high towards deep midwicket or cow corner against spin bowling.",
        "aliases": ["Power Sweep", "Lofted Sweep"],
        "tags": ["sweep", "attacking", "aerial", "power"],
        "difficulty": "Advanced",
        "analysis_features": [
            "lead_knee_flexion",
            "torso_rotation",
            "lead_arm_extension",
            "follow_through_height",
            "head_stability"
        ],
        "reference_id": "ref_slog_sweep_rohit",
        "reference_status": "available",
        "reference_title": "Rohit Sharma / Suryakumar Yadav — Aggressive Slog Sweep",
        "reference_player": "Rohit Sharma / Suryakumar Yadav",
        "reference_source": "IPL Official Powerhitting Benchmark & ICC",
        "reference_video_url": "/api/video/original/sample_slog_sweep.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_slog_sweep_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Combines knee drop base of traditional sweep with explosive hip uncoiling and high follow-through for maximum elevation."
    },
    {
        "id": "shot_reverse_sweep",
        "slug": "reverse-sweep",
        "name": "Reverse Sweep",
        "category": "Sweep-family Strokes",
        "description": "A sweep-style stroke directing the ball towards the off side through backward point by reversing the bat face orientation and hand action.",
        "aliases": ["Reverse Paddle", "Off-side Sweep"],
        "tags": ["sweep", "innovative", "off-side", "reverse"],
        "difficulty": "Advanced",
        "analysis_features": [
            "lead_knee_flexion",
            "rear_knee_flexion",
            "torso_lowering",
            "wrist_rotation",
            "head_stability"
        ],
        "reference_id": "ref_reverse_sweep_pant",
        "reference_status": "available",
        "reference_title": "Glenn Maxwell / Rishabh Pant — Tactical Reverse Sweep",
        "reference_player": "Glenn Maxwell / Rishabh Pant",
        "reference_source": "IPL Technical Innovation Analysis & ICC",
        "reference_video_url": "/api/video/original/sample_reverse_sweep.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_reverse_sweep_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Hands rotate so back of top hand faces bowler; bat strikes from leg to off side across the body."
    },
    {
        "id": "shot_paddle_sweep",
        "slug": "paddle-sweep",
        "name": "Paddle Sweep",
        "category": "Sweep-family Strokes",
        "description": "A softer sweep deflection using a flatter bat angle to deflect a full delivery fine of square leg or down to fine leg.",
        "aliases": ["Paddle", "Fine Sweep"],
        "tags": ["sweep", "touch", "deflection", "spin"],
        "difficulty": "Advanced",
        "analysis_features": [
            "lead_knee_flexion",
            "rear_knee_flexion",
            "wrist_softness",
            "head_over_knee"
        ],
        "reference_id": "ref_paddle_sweep_sachin",
        "reference_status": "available",
        "reference_title": "Sachin Tendulkar / Rishabh Pant — Fine Paddle Sweep",
        "reference_player": "Sachin Tendulkar / Rishabh Pant",
        "reference_source": "ICC Masterclass on Manipulating Field Placements",
        "reference_video_url": "/api/video/original/sample_paddle_sweep.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_paddle_sweep_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Bat blade acts as a ramp with soft contact, using incoming ball energy rather than forceful strike."
    },

    # ---------------------------------------------------------
    # Category 7: Power and Innovative Shots (5 shots)
    # ---------------------------------------------------------
    {
        "id": "shot_slog",
        "slug": "slog",
        "name": "Slog",
        "category": "Power and Innovative Shots",
        "description": "A powerful, aggressive attacking stroke, generally aimed towards the leg side boundary with maximum bat speed and full body rotation.",
        "aliases": ["Cow Corner Hit", "Heave"],
        "tags": ["power", "attacking", "leg-side", "aerial"],
        "difficulty": "Intermediate",
        "analysis_features": [
            "lead_knee_flexion",
            "torso_rotation",
            "lead_arm_extension",
            "follow_through_height",
            "balance_recovery"
        ],
        "reference_id": "ref_slog_yuvraj",
        "reference_status": "available",
        "reference_title": "Rohit Sharma / Yuvraj Singh — Explosive Boundary Slog",
        "reference_player": "Rohit Sharma / Yuvraj Singh",
        "reference_source": "ICC World Cup Powerhitting Archive",
        "reference_video_url": "/api/video/original/sample_slog.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_slog_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Base must remain grounded through initial swing; arms clear hips to permit violent arc."
    },
    {
        "id": "shot_switch_hit",
        "slug": "switch-hit",
        "name": "Switch Hit",
        "category": "Power and Innovative Shots",
        "description": "An innovative stroke in which the batter completely mirrors stance and grip (e.g. from right-handed to left-handed) immediately before the delivery.",
        "aliases": ["Switch Stance Hit"],
        "tags": ["innovative", "stance-switch", "ambidextrous"],
        "difficulty": "Elite",
        "analysis_features": [
            "stance_transition_timing",
            "hip_reversal",
            "torso_rotation",
            "balance_stability"
        ],
        "reference_id": "ref_switch_hit_warner",
        "reference_status": "available",
        "reference_title": "David Warner / Kevin Pietersen — Ambidextrous Switch Hit",
        "reference_player": "Kevin Pietersen / David Warner",
        "reference_source": "ICC Technical Benchmark for Innovative Strokes",
        "reference_video_url": "/api/video/original/sample_switch_hit.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_switch_hit_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Requires rapid foot crossover and complete hand reversal while retaining visual fixation on bowler release."
    },
    {
        "id": "shot_scoop_shot",
        "slug": "scoop-shot",
        "name": "Scoop Shot",
        "category": "Power and Innovative Shots",
        "description": "An unorthodox shot using an upward, ramping bat path to direct a full delivery directly over the wicketkeeper's head towards fine leg.",
        "aliases": ["Dilscoop", "Over-keeper Scoop"],
        "tags": ["innovative", "aerial", "ramp", "high-risk"],
        "difficulty": "Elite",
        "analysis_features": [
            "lead_knee_flexion",
            "rear_knee_flexion",
            "torso_lowering",
            "head_stability",
            "upward_arm_extension"
        ],
        "reference_id": "ref_scoop_surya",
        "reference_status": "available",
        "reference_title": "Suryakumar Yadav — 360° Over-Keeper Scoop",
        "reference_player": "Suryakumar Yadav",
        "reference_source": "BCCI & IPL 360° Innovation Benchmark",
        "reference_video_url": "/api/video/original/sample_scoop_shot.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_scoop_shot_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Batter drops low directly in line of ball, creating an upward ramp face; head must stay still despite incoming delivery."
    },
    {
        "id": "shot_ramp_shot",
        "slug": "ramp-shot",
        "name": "Ramp Shot",
        "category": "Power and Innovative Shots",
        "description": "A guided stroke that angles the bat face backwards to deflect a fast short or good-length delivery over third man or fine leg.",
        "aliases": ["Upper Ramp", "Pace Deflection Ramp"],
        "tags": ["innovative", "deflection", "ramp"],
        "difficulty": "Advanced",
        "analysis_features": [
            "wrist_softness",
            "lead_arm_extension",
            "torso_inclination",
            "head_stability"
        ],
        "reference_id": "ref_ramp_surya",
        "reference_status": "available",
        "reference_title": "Suryakumar Yadav / Rishabh Pant — Pace Deflection Ramp",
        "reference_player": "Suryakumar Yadav / Rishabh Pant",
        "reference_source": "IPL Official Match Benchmark & BCCI",
        "reference_video_url": "/api/video/original/sample_ramp_shot.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_ramp_shot_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Relies on bowler's pace; minimal follow-through with emphasis on blade tilt."
    },
    {
        "id": "shot_helicopter_shot",
        "slug": "helicopter-shot",
        "name": "Helicopter Shot",
        "category": "Power and Innovative Shots",
        "description": "A distinctive power stroke against full or yorker-length deliveries, characterized by extreme wrist snap and an explosive 360-degree overhead bat follow-through.",
        "aliases": ["Wrist Snap Heave", "Dhoni Helicopter"],
        "tags": ["innovative", "power", "wrist-snap", "yorker-counter"],
        "difficulty": "Elite",
        "analysis_features": [
            "rear_knee_flexion",
            "torso_rotation",
            "follow_through_height",
            "wrist_snap_velocity",
            "post_shot_balance"
        ],
        "reference_id": "ref_helicopter_dhoni",
        "reference_status": "available",
        "reference_title": "MS Dhoni — Trademark Yorker Helicopter Shot",
        "reference_player": "MS Dhoni",
        "reference_source": "BCCI & IPL Trademark Power Benchmark",
        "reference_video_url": "/api/video/original/sample_helicopter_shot.mp4",
        "reference_thumbnail_url": "/api/video/thumbnail/sample_helicopter_shot_thumb.jpg",
        "implementation_status": "supported",
        "technique_notes": "Wrists snap forcefully at point of contact below knee level; circular follow-through dissipates intense rotational momentum."
    }
]

def get_shot_catalogue() -> List[Dict[str, Any]]:
    """Returns the complete 25-shot catalogue."""
    return SHOT_CATALOGUE

def get_shot_by_id_or_slug(identifier: str) -> Optional[Dict[str, Any]]:
    """Resolves a shot by ID, slug, or exact/fuzzy name."""
    clean = identifier.strip().lower()
    for s in SHOT_CATALOGUE:
        if s["id"].lower() == clean or s["slug"].lower() == clean or s["name"].lower() == clean:
            return s
        if clean in [a.lower() for a in s["aliases"]]:
            return s
    
    # Generic mapping
    if "cover" in clean and "drive" in clean:
        return get_shot_by_id_or_slug("cover-drive")
    if "straight" in clean and "drive" in clean:
        return get_shot_by_id_or_slug("straight-drive")
    if "on" in clean and "drive" in clean:
        return get_shot_by_id_or_slug("on-drive")
    if "off" in clean and "drive" in clean:
        return get_shot_by_id_or_slug("off-drive")
    if "lofted" in clean and "drive" in clean:
        return get_shot_by_id_or_slug("lofted-drive")
    if "pull" in clean:
        return get_shot_by_id_or_slug("pull-shot")
    if "hook" in clean:
        return get_shot_by_id_or_slug("hook-shot")
    if "forward" in clean and "defensive" in clean:
        return get_shot_by_id_or_slug("forward-defensive")
    if "back" in clean and "defensive" in clean:
        return get_shot_by_id_or_slug("back-foot-defensive")
    if "punch" in clean:
        return get_shot_by_id_or_slug("back-foot-punch")
    if "square" in clean and "cut" in clean:
        return get_shot_by_id_or_slug("square-cut")
    if "late" in clean and "cut" in clean:
        return get_shot_by_id_or_slug("late-cut")
    if "upper" in clean and "cut" in clean:
        return get_shot_by_id_or_slug("upper-cut")
    if "flick" in clean:
        return get_shot_by_id_or_slug("flick-shot")
    if "glance" in clean:
        return get_shot_by_id_or_slug("leg-glance")
    if "clip" in clean:
        return get_shot_by_id_or_slug("clip-shot")
    if "slog" in clean and "sweep" in clean:
        return get_shot_by_id_or_slug("slog-sweep")
    if "reverse" in clean and "sweep" in clean:
        return get_shot_by_id_or_slug("reverse-sweep")
    if "paddle" in clean and "sweep" in clean:
        return get_shot_by_id_or_slug("paddle-sweep")
    if "sweep" in clean:
        return get_shot_by_id_or_slug("sweep")
    if "helicopter" in clean:
        return get_shot_by_id_or_slug("helicopter-shot")
    if "scoop" in clean:
        return get_shot_by_id_or_slug("scoop-shot")
    if "ramp" in clean:
        return get_shot_by_id_or_slug("ramp-shot")
    if "switch" in clean:
        return get_shot_by_id_or_slug("switch-hit")
    if "slog" in clean:
        return get_shot_by_id_or_slug("slog")
        
    return None

def resolve_shot_category(shot_name: str) -> str:
    """Finds the category for a shot name, or returns 'Other' if unclassified."""
    shot = get_shot_by_id_or_slug(shot_name)
    if shot:
        return shot["category"]
    return "Other"
