"""
Builds frontend/src/data/shotAnimations.ts with complete, distinct 3D biomechanical keyframe animations
for all 25 cricket shots in CricketIQ.
Provenance: "authored baseline (tunable)".
"""

import json
from pathlib import Path

# Complete definitions for all 25 shots with realistic biomechanical profiles
SHOTS = [
    {
        "id": "cover_drive",
        "name": "Cover Drive",
        "slug": "cover-drive",
        "category": "Drives",
        "swingPlane": "angled_off",
        "ball": {
            "line": "Off stump to 5th stump",
            "length": "Full / driving length",
            "pitch": [0.65, 0.0, 0.28],
            "contact": [0.38, 0.42, 0.24]
        },
        "mistakes": [
            "Reaching with the hands without committing front foot to pitch of ball",
            "Dropping lead elbow causing an uncontrolled aerial slice to point",
            "Torso falling away to leg side losing stability at impact"
        ],
        "drills": [
            "Drop-ball drive off tee through cone corridor at extra cover",
            "Lead-elbow focus drill with dominant top-hand grip check",
            "Impact pause drill holding finish for 3 seconds"
        ],
        "cues": {
            "stance": "Relaxed stance, eyes level, hands resting comfortably at back hip",
            "backlift": "Bat raised toward second/third slip, top hand dominant",
            "stride": "Front foot strides smoothly towards extra cover, head leading",
            "downswing": "High lead elbow directs bat pendulum smoothly through the off-side arc",
            "impact": "Contact directly beneath the eyes with vertical-angled face",
            "follow_through": "High sweeping finish across front shoulder, holding balance",
            "recovery": "Controlled deceleration and reset back to batting crease"
        },
        "hip": [0.12, 0.88, 0.08],
        "leadStride": [0.42, 0.0, 0.22],
        "rearFoot": [-0.15, 0.0, -0.05],
        "handle": [0.24, 0.76, 0.18],
        "batTip": [0.38, 0.20, 0.24],
        "batAngle": 18.0,
        "leadKnee": 122.0,
        "rearKnee": 158.0,
        "leadElbow": 140.0,
        "rearElbow": 90.0,
        "torsoLean": 26.0,
        "torsoSideLean": 12.0,
        "torsoRot": -18.0,
        "ftBatAngle": -75.0,
        "ftBatTip": [0.28, 1.72, 0.32],
        "kneeling": False
    },
    {
        "id": "straight_drive",
        "name": "Straight Drive",
        "slug": "straight-drive",
        "category": "Drives",
        "swingPlane": "vertical",
        "ball": {
            "line": "Middle to off stump",
            "length": "Full / driving length",
            "pitch": [0.70, 0.0, 0.02],
            "contact": [0.40, 0.38, 0.0]
        },
        "mistakes": [
            "Playing around front pad instead of striding straight down ground",
            "Hitting on the up without getting head stationed over ball",
            "Bottom hand taking over causing skewed ball elevation"
        ],
        "drills": [
            "Straight alley corridor drill between two parallel lines",
            "Top hand only driving with weighted bat",
            "Underarm feed straight back past bowling stumps"
        ],
        "cues": {
            "stance": "Balanced upright stance, weight evenly on balls of feet",
            "backlift": "Straight backlift straight towards middle/off stumps",
            "stride": "Decisive front foot stride straight down the pitch",
            "downswing": "Pure vertical pendulum swing leading with sharp lead elbow",
            "impact": "Full face of bat presented straight back down ground",
            "follow_through": "High textbook finish, full bat face showing to bowler",
            "recovery": "Smooth weight re-centering onto neutral crease line"
        },
        "hip": [0.14, 0.87, 0.0],
        "leadStride": [0.48, 0.0, 0.0],
        "rearFoot": [-0.15, 0.0, -0.02],
        "handle": [0.28, 0.74, 0.02],
        "batTip": [0.40, 0.18, 0.0],
        "batAngle": 12.0,
        "leadKnee": 118.0,
        "rearKnee": 160.0,
        "leadElbow": 145.0,
        "rearElbow": 92.0,
        "torsoLean": 28.0,
        "torsoSideLean": 0.0,
        "torsoRot": -4.0,
        "ftBatAngle": -82.0,
        "ftBatTip": [0.35, 1.78, 0.02],
        "kneeling": False
    },
    {
        "id": "on_drive",
        "name": "On Drive",
        "slug": "on-drive",
        "category": "Drives",
        "swingPlane": "angled_leg",
        "ball": {
            "line": "Middle and leg stump",
            "length": "Full / half-volley",
            "pitch": [0.66, 0.0, -0.16],
            "contact": [0.36, 0.40, -0.12]
        },
        "mistakes": [
            "Closing front shoulder prematurely causing leading edge",
            "Planting front leg across line of ball blocking bat swing",
            "Excessive wrist turn causing mis-hit to midwicket"
        ],
        "drills": [
            "Mid-on target drill hitting past bowler's leg-side stump",
            "Open hip alignment drill maintaining side-on head positioning",
            "Tennis ball drop drill on leg stump line"
        ],
        "cues": {
            "stance": "Square hips, relaxed knees, head steady on middle-and-leg line",
            "backlift": "Slightly angled backlift past off stump, open shoulder line",
            "stride": "Front foot steps straight down pitch slightly towards mid-on",
            "downswing": "Bat path accelerates smoothly toward mid-on",
            "impact": "Crisp contact under nose with vertical face directed to mid-on",
            "follow_through": "Extending high toward mid-on with chest open to target",
            "recovery": "Controlled balance check and push back"
        },
        "hip": [0.11, 0.89, -0.05],
        "leadStride": [0.44, 0.0, -0.12],
        "rearFoot": [-0.14, 0.0, -0.04],
        "handle": [0.22, 0.75, -0.08],
        "batTip": [0.36, 0.20, -0.12],
        "batAngle": 14.0,
        "leadKnee": 120.0,
        "rearKnee": 158.0,
        "leadElbow": 138.0,
        "rearElbow": 95.0,
        "torsoLean": 25.0,
        "torsoSideLean": -6.0,
        "torsoRot": 14.0,
        "ftBatAngle": -72.0,
        "ftBatTip": [0.24, 1.70, -0.18],
        "kneeling": False
    },
    {
        "id": "off_drive",
        "name": "Off Drive",
        "slug": "off-drive",
        "category": "Drives",
        "swingPlane": "angled_off",
        "ball": {
            "line": "Off stump corridor",
            "length": "Full driving length",
            "pitch": [0.68, 0.0, 0.18],
            "contact": [0.38, 0.40, 0.15]
        },
        "mistakes": [
            "Pushing hands away from body line without shoulder turn",
            "Falling over to off side before impact",
            "Failing to transfer weight fully to front knee"
        ],
        "drills": [
            "Cone alley to wide mid-off",
            "Forward lunge stability hold with bat extended",
            "Two-bounce drive drill with front shoulder pointing to target"
        ],
        "cues": {
            "stance": "Side-on stance, chin on front shoulder",
            "backlift": "Backlift aimed at second slip with firm top wrist",
            "stride": "Front foot strides smoothly to mid-off line",
            "downswing": "Lead elbow leads downswing through off-side corridor",
            "impact": "Clean punch through mid-off with high vertical elbow",
            "follow_through": "Fluid finish high toward mid-off",
            "recovery": "Step back into neutral stance"
        },
        "hip": [0.12, 0.88, 0.05],
        "leadStride": [0.45, 0.0, 0.14],
        "rearFoot": [-0.15, 0.0, -0.04],
        "handle": [0.25, 0.75, 0.10],
        "batTip": [0.38, 0.19, 0.15],
        "batAngle": 16.0,
        "leadKnee": 121.0,
        "rearKnee": 159.0,
        "leadElbow": 142.0,
        "rearElbow": 92.0,
        "torsoLean": 27.0,
        "torsoSideLean": 8.0,
        "torsoRot": -12.0,
        "ftBatAngle": -78.0,
        "ftBatTip": [0.30, 1.74, 0.20],
        "kneeling": False
    },
    {
        "id": "lofted_drive",
        "name": "Lofted Drive",
        "slug": "lofted-drive",
        "category": "Drives",
        "swingPlane": "overhead",
        "ball": {
            "line": "Middle to off stump",
            "length": "Full / overpitched",
            "pitch": [0.72, 0.0, 0.05],
            "contact": [0.42, 0.46, 0.04]
        },
        "mistakes": [
            "Slashing with bottom hand while pulling head back",
            "Hitting ball too early before getting under trajectory",
            "Losing base by jumping off back foot prematurely"
        ],
        "drills": [
            "Launch angle lofting over 30-yard inner circle rope",
            "Medicine ball overhead extension toss",
            "Drop-feed aerial driving drill over boundary cones"
        ],
        "cues": {
            "stance": "Athletic deep flexed base, relaxed power grip",
            "backlift": "High exaggerated backlift over right shoulder",
            "stride": "Firm stride to ball pitch, creating launch clearance",
            "downswing": "Accelerating upward arc from underneath the ball line",
            "impact": "Clean extension lifting ball over infield with full swing",
            "follow_through": "Towering high finish over head with arms fully extended",
            "recovery": "Land on firm front foot and recover"
        },
        "hip": [0.16, 0.85, 0.02],
        "leadStride": [0.46, 0.0, 0.06],
        "rearFoot": [-0.14, 0.0, -0.02],
        "handle": [0.30, 0.78, 0.05],
        "batTip": [0.44, 0.32, 0.04],
        "batAngle": 38.0,
        "leadKnee": 126.0,
        "rearKnee": 150.0,
        "leadElbow": 155.0,
        "rearElbow": 130.0,
        "torsoLean": 18.0,
        "torsoSideLean": 2.0,
        "torsoRot": -10.0,
        "ftBatAngle": -115.0,
        "ftBatTip": [0.42, 1.95, 0.06],
        "kneeling": False
    },
    {
        "id": "forward_defensive",
        "name": "Forward Defensive",
        "slug": "forward-defensive",
        "category": "Defensive Strokes",
        "swingPlane": "vertical",
        "ball": {
            "line": "Off stump channel",
            "length": "Good length probing top of off",
            "pitch": [0.60, 0.0, 0.12],
            "contact": [0.28, 0.44, 0.10]
        },
        "mistakes": [
            "Hard hands pushing at ball away from body line",
            "Bat angled upward leading to catches in gully / slips",
            "Head staying back behind crease without covering off stump"
        ],
        "drills": [
            "Dead-bat drop drill making ball stop dead within 1 meter",
            "Soft hands tennis ball block with bottom hand fingers off handle",
            "Blind bounce defensive block under direct eye line"
        ],
        "cues": {
            "stance": "Solid defensive stance, low hands, compact base",
            "backlift": "Short, controlled backlift straight over off stump",
            "stride": "Short positive stride to ball line, front knee flexed",
            "downswing": "Bat descends softly close to the front pad",
            "impact": "Soft dead vertical bat directly beneath the eyes, angling to ground",
            "follow_through": "Zero follow-through: bat held dead at point of contact",
            "recovery": "Step back securely into defensive crease"
        },
        "hip": [0.08, 0.89, 0.03],
        "leadStride": [0.28, 0.0, 0.08],
        "rearFoot": [-0.15, 0.0, -0.04],
        "handle": [0.20, 0.76, 0.08],
        "batTip": [0.28, 0.15, 0.09],
        "batAngle": 6.0,
        "leadKnee": 128.0,
        "rearKnee": 162.0,
        "leadElbow": 125.0,
        "rearElbow": 85.0,
        "torsoLean": 24.0,
        "torsoSideLean": 4.0,
        "torsoRot": -8.0,
        "ftBatAngle": 6.0,
        "ftBatTip": [0.28, 0.15, 0.09],
        "kneeling": False
    },
    {
        "id": "back_foot_defensive",
        "name": "Back-foot Defensive",
        "slug": "back-foot-defensive",
        "category": "Defensive Strokes",
        "swingPlane": "vertical",
        "ball": {
            "line": "Middle and off stump",
            "length": "Back of a length rising to ribs",
            "pitch": [0.45, 0.0, 0.08],
            "contact": [-0.10, 0.82, 0.06]
        },
        "mistakes": [
            "Backing away to square leg instead of back and across",
            "Playing away from torso with stiff arms",
            "Not getting tall on balls of feet to ride bounce"
        ],
        "drills": [
            "Back-and-across footwork grid marking off stump alignment",
            "Side throwdowns from short distance with heavy tennis ball",
            "Bounce-riding drill absorbing impact into soft turf"
        ],
        "cues": {
            "stance": "Ready stance, alert to back-of-a-length bounce",
            "backlift": "Compact cocked wrists lifting bat vertically behind back shoulder",
            "stride": "Step back and across onto rear foot, rising tall",
            "downswing": "Bat drops vertically under the armpits close to chest",
            "impact": "Vertical bat drops ball softly at batter's feet under the eyes",
            "follow_through": "Compact hold: no follow-through swing",
            "recovery": "Re-center weight squarely into crease"
        },
        "hip": [-0.14, 0.94, 0.06],
        "leadStride": [0.05, 0.0, 0.02],
        "rearFoot": [-0.20, 0.0, 0.08],
        "handle": [-0.10, 0.98, 0.06],
        "batTip": [-0.10, 0.35, 0.06],
        "batAngle": 3.0,
        "leadKnee": 160.0,
        "rearKnee": 146.0,
        "leadElbow": 105.0,
        "rearElbow": 80.0,
        "torsoLean": 8.0,
        "torsoSideLean": 2.0,
        "torsoRot": -5.0,
        "ftBatAngle": 3.0,
        "ftBatTip": [-0.10, 0.35, 0.06],
        "kneeling": False
    },
    {
        "id": "back_foot_punch",
        "name": "Back-foot Punch",
        "slug": "back-foot-punch",
        "category": "Back-foot and Cut Shots",
        "swingPlane": "vertical",
        "ball": {
            "line": "Just outside off stump corridor",
            "length": "Short of a length with true bounce",
            "pitch": [0.48, 0.0, 0.20],
            "contact": [-0.08, 0.78, 0.18]
        },
        "mistakes": [
            "Slashing across the line instead of punching through off side",
            "Weight collapsing back onto heels losing punch authority",
            "Separating hands from body too early"
        ],
        "drills": [
            "Off-side corridor punch off elevated bowling machine",
            "Back foot rise and punch drill with medicine ball pass",
            "Target markers through cover point from back foot"
        ],
        "cues": {
            "stance": "Dynamic base ready to spring back and across",
            "backlift": "High straight backlift above back shoulder",
            "stride": "Decisive back and across trigger onto rear ball of foot",
            "downswing": "Elbows lead crisp vertical punch directly at point/cover",
            "impact": "Clean punch on rise under eyes, transferring momentum forward",
            "follow_through": "Arms extend through the stroke with wrists firm",
            "recovery": "Controlled step back to neutral stance"
        },
        "hip": [-0.12, 0.93, 0.08],
        "leadStride": [0.08, 0.0, 0.04],
        "rearFoot": [-0.18, 0.0, 0.10],
        "handle": [-0.04, 0.92, 0.14],
        "batTip": [0.06, 0.32, 0.18],
        "batAngle": 14.0,
        "leadKnee": 158.0,
        "rearKnee": 144.0,
        "leadElbow": 132.0,
        "rearElbow": 96.0,
        "torsoLean": 12.0,
        "torsoSideLean": 6.0,
        "torsoRot": -12.0,
        "ftBatAngle": -55.0,
        "ftBatTip": [0.18, 1.45, 0.22],
        "kneeling": False
    },
    {
        "id": "square_cut",
        "name": "Square Cut",
        "slug": "square-cut",
        "category": "Back-foot and Cut Shots",
        "swingPlane": "horizontal",
        "ball": {
            "line": "Wide outside off stump",
            "length": "Short / back of length with width",
            "pitch": [0.42, 0.0, 0.40],
            "contact": [-0.06, 0.72, 0.42]
        },
        "mistakes": [
            "Cutting balls too close to off stump resulting in inside edge",
            "Hitting on an upward plane giving catches to backward point",
            "Failing to roll wrists on top of the bounce"
        ],
        "drills": [
            "High to low wood chop drill onto turf through point",
            "Side throwdown with maximum width targeting backward point",
            "Wrist roll snap drill on suspended ball"
        ],
        "cues": {
            "stance": "Balanced stance ready to shift back and across",
            "backlift": "High backlift cocked high over right shoulder",
            "stride": "Back foot moves back and across to off stump, giving arms room",
            "downswing": "Horizontal slashing swing descending from high to low",
            "impact": "Ball struck level with body at backward point, wrists rolling over",
            "follow_through": "Blade finishes low past off hip rolling wrists",
            "recovery": "Swivel back into batting crease"
        },
        "hip": [-0.16, 0.91, 0.12],
        "leadStride": [0.02, 0.0, 0.06],
        "rearFoot": [-0.22, 0.0, 0.14],
        "handle": [-0.12, 0.88, 0.28],
        "batTip": [-0.02, 0.70, 0.55],
        "batAngle": 86.0,
        "leadKnee": 162.0,
        "rearKnee": 138.0,
        "leadElbow": 120.0,
        "rearElbow": 115.0,
        "torsoLean": 10.0,
        "torsoSideLean": 18.0,
        "torsoRot": -22.0,
        "ftBatAngle": 110.0,
        "ftBatTip": [0.04, 0.48, 0.46],
        "kneeling": False
    },
    {
        "id": "late_cut",
        "name": "Late Cut",
        "slug": "late-cut",
        "category": "Back-foot and Cut Shots",
        "swingPlane": "horizontal",
        "ball": {
            "line": "Outside off stump corridor",
            "length": "Short of a length / spinner turning away",
            "pitch": [0.44, 0.0, 0.32],
            "contact": [-0.18, 0.68, 0.34]
        },
        "mistakes": [
            "Making contact too early in front of the body",
            "Hard bottom hand slashing rather than soft wrist guiding",
            "Missing the line and chopping onto stumps"
        ],
        "drills": [
            "Catching ball deep near keeper's gloves before soft glide",
            "Spinner deflection drill hitting into target bucket at third man",
            "Soft wrists tennis ball deflection exercise"
        ],
        "cues": {
            "stance": "Patience stance, waiting deep in the crease",
            "backlift": "Short neat backlift lifted late as ball arrives",
            "stride": "Step back and across deep inside crease line",
            "downswing": "Soft open face blade drops late behind the body line",
            "impact": "Glanced off open face past slip cordon towards third man",
            "follow_through": "Delicate check finish with open blade pointing to third man",
            "recovery": "Step reset into neutral position"
        },
        "hip": [-0.18, 0.92, 0.10],
        "leadStride": [-0.02, 0.0, 0.04],
        "rearFoot": [-0.24, 0.0, 0.12],
        "handle": [-0.18, 0.85, 0.22],
        "batTip": [-0.12, 0.42, 0.36],
        "batAngle": 58.0,
        "leadKnee": 164.0,
        "rearKnee": 140.0,
        "leadElbow": 112.0,
        "rearElbow": 100.0,
        "torsoLean": 8.0,
        "torsoSideLean": 14.0,
        "torsoRot": -15.0,
        "ftBatAngle": 68.0,
        "ftBatTip": [-0.08, 0.36, 0.38],
        "kneeling": False
    },
    {
        "id": "upper_cut",
        "name": "Upper Cut",
        "slug": "upper-cut",
        "category": "Back-foot and Cut Shots",
        "swingPlane": "overhead",
        "ball": {
            "line": "Outside off stump bouncer",
            "length": "Short bouncer rising above shoulder",
            "pitch": [0.35, 0.0, 0.30],
            "contact": [-0.12, 1.35, 0.32]
        },
        "mistakes": [
            "Attempting to pull a ball too wide outside off",
            "Failing to guide the ball high over slips, hitting to fly slip",
            "Losing sight of fast bouncer under the helmet visor"
        ],
        "drills": [
            "High ramp drill using bouncers off trampette",
            "Over-the-shoulder glide visualization and execution",
            "Light bat quick-hands reaction drill on short balls"
        ],
        "cues": {
            "stance": "Tall stance observing bowler trajectory closely",
            "backlift": "Quick cock of wrists high above right ear",
            "stride": "Back foot steps back and slightly arches to create upper view",
            "downswing": "Bat angles backward and upward under the high ball",
            "impact": "Open bat face ramps bouncer gracefully over slips to third man",
            "follow_through": "High guided extension over right shoulder toward third man boundary",
            "recovery": "Rebalance onto balls of feet"
        },
        "hip": [-0.15, 0.95, 0.08],
        "leadStride": [0.0, 0.0, 0.04],
        "rearFoot": [-0.20, 0.0, 0.10],
        "handle": [-0.14, 1.25, 0.24],
        "batTip": [-0.08, 1.68, 0.36],
        "batAngle": -42.0,
        "leadKnee": 165.0,
        "rearKnee": 150.0,
        "leadElbow": 135.0,
        "rearElbow": 125.0,
        "torsoLean": -4.0,
        "torsoSideLean": 10.0,
        "torsoRot": -18.0,
        "ftBatAngle": -75.0,
        "ftBatTip": [-0.02, 1.88, 0.38],
        "kneeling": False
    },
    {
        "id": "pull_shot",
        "name": "Pull Shot",
        "slug": "pull-shot",
        "category": "Short-ball Attacking Shots",
        "swingPlane": "horizontal",
        "ball": {
            "line": "Middle to leg stump line",
            "length": "Short ball waist to chest high",
            "pitch": [0.38, 0.0, -0.06],
            "contact": [-0.05, 0.88, -0.15]
        },
        "mistakes": [
            "Back foot not going back and across, getting cramped",
            "Bottom hand taking bat upward causing top edges to fine leg",
            "Head pulling away before impact with eyes closed"
        ],
        "drills": [
            "Waist-height horizontal swing drill rolling wrists down",
            "Medicine ball rotational throw across lead hip",
            "Underarm short-bounce pull into target net at square leg"
        ],
        "cues": {
            "stance": "Athletic ready stance, ready to spring onto back foot",
            "backlift": "High backlift over off shoulder, arms extended",
            "stride": "Back foot shifts back and across, front leg pivots clear",
            "downswing": "Horizontal bat plane swivels powerfully across the chest line",
            "impact": "Impact out in front of chest, rolling wrists over top of ball",
            "follow_through": "Full rotational follow-through wrapping around left shoulder",
            "recovery": "Pivot on rear toe and return to balanced stance"
        },
        "hip": [-0.10, 0.92, -0.04],
        "leadStride": [0.08, 0.0, -0.08],
        "rearFoot": [-0.18, 0.0, 0.02],
        "handle": [-0.08, 0.95, -0.05],
        "batTip": [0.08, 0.92, -0.42],
        "batAngle": 92.0,
        "leadKnee": 152.0,
        "rearKnee": 136.0,
        "leadElbow": 138.0,
        "rearElbow": 124.0,
        "torsoLean": 6.0,
        "torsoSideLean": -4.0,
        "torsoRot": 42.0,
        "ftBatAngle": 155.0,
        "ftBatTip": [-0.15, 1.15, -0.48],
        "kneeling": False
    },
    {
        "id": "hook_shot",
        "name": "Hook Shot",
        "slug": "hook-shot",
        "category": "Short-ball Attacking Shots",
        "swingPlane": "horizontal",
        "ball": {
            "line": "Head / helmet height on off stump",
            "length": "Aggressive short bouncer",
            "pitch": [0.32, 0.0, 0.0],
            "contact": [-0.08, 1.48, -0.10]
        },
        "mistakes": [
            "Taking eyes off high bouncer at moment of stroke",
            "Top edging over wicketkeeper by swinging under ball",
            "Weight caught falling backwards off balance"
        ],
        "drills": [
            "Tennis ball chest-to-helmet hook swivel off rebound wall",
            "Core rotational power drill with cable machine",
            "Bouncer control drill hitting down to fine leg"
        ],
        "cues": {
            "stance": "Tall stance tracking bowler release point",
            "backlift": "Very high backlift above head height",
            "stride": "Back foot steps back and swivels inside line of delivery",
            "downswing": "Violent horizontal swivel swing at shoulder/helmet level",
            "impact": "Contact high in front of helmet, rolling wrists down to turf",
            "follow_through": "Complete 180-degree upper torso rotation to backward square",
            "recovery": "Steady feet and re-center"
        },
        "hip": [-0.12, 0.94, -0.02],
        "leadStride": [0.04, 0.0, -0.06],
        "rearFoot": [-0.18, 0.0, 0.04],
        "handle": [-0.10, 1.42, -0.04],
        "batTip": [0.04, 1.46, -0.44],
        "batAngle": 95.0,
        "leadKnee": 155.0,
        "rearKnee": 140.0,
        "leadElbow": 142.0,
        "rearElbow": 130.0,
        "torsoLean": 2.0,
        "torsoSideLean": -6.0,
        "torsoRot": 55.0,
        "ftBatAngle": 165.0,
        "ftBatTip": [-0.20, 1.38, -0.45],
        "kneeling": False
    },
    {
        "id": "flick_shot",
        "name": "Flick Shot",
        "slug": "flick-shot",
        "category": "Leg-side and Wrist-oriented Strokes",
        "swingPlane": "angled_leg",
        "ball": {
            "line": "Leg stump to pads",
            "length": "Full / yorker length on pads",
            "pitch": [0.65, 0.0, -0.15],
            "contact": [0.34, 0.36, -0.14]
        },
        "mistakes": [
            "Falling over to off side closing off leg-side swing",
            "Flicking with stiff wrists instead of supple whip",
            "Playing too early leading to aerial chip to mid-on"
        ],
        "drills": [
            "Pad-line flick target drill past square leg umpire",
            "Wrist flick resistance band snap exercise",
            "Underarm half-volley flick into target net at midwicket"
        ],
        "cues": {
            "stance": "Side-on stance, balanced head over middle stump",
            "backlift": "Straight backlift, keeping hands inside line of body",
            "stride": "Front foot steps down towards ball line, head locked over ball",
            "downswing": "Straight pendulum converts into sudden wrist whip on contact",
            "impact": "Supple wrists roll blade face across ball towards midwicket",
            "follow_through": "Fluid wrist whip finishing around front hip/ribs",
            "recovery": "Controlled step back into stance"
        },
        "hip": [0.10, 0.88, -0.04],
        "leadStride": [0.38, 0.0, -0.12],
        "rearFoot": [-0.14, 0.0, -0.02],
        "handle": [0.22, 0.72, -0.10],
        "batTip": [0.34, 0.22, -0.18],
        "batAngle": 18.0,
        "leadKnee": 124.0,
        "rearKnee": 156.0,
        "leadElbow": 130.0,
        "rearElbow": 110.0,
        "torsoLean": 24.0,
        "torsoSideLean": -5.0,
        "torsoRot": 22.0,
        "ftBatAngle": -45.0,
        "ftBatTip": [0.15, 1.48, -0.28],
        "kneeling": False
    },
    {
        "id": "leg_glance",
        "name": "Leg Glance",
        "slug": "leg-glance",
        "category": "Leg-side and Wrist-oriented Strokes",
        "swingPlane": "angled_leg",
        "ball": {
            "line": "Drifting down leg side",
            "length": "Good length onto hip/thigh",
            "pitch": [0.55, 0.0, -0.20],
            "contact": [0.18, 0.55, -0.18]
        },
        "mistakes": [
            "Closing bat face too violently deflecting onto stumps",
            "Stiff wrists robbing touch and precision",
            "Over-striding across the stumps losing sight of ball"
        ],
        "drills": [
            "Fine leg deflector target drill into miniature goal",
            "Soft wrist touch drill using squash balls",
            "Front pad glance with loose bottom hand grip"
        ],
        "cues": {
            "stance": "Calm balanced stance watching ball outside leg stump",
            "backlift": "Straight backlift with relaxed wrists",
            "stride": "Subtle step forward or back depending on length, head on line",
            "downswing": "Gentle descent using bowler's pace",
            "impact": "Blade face turned slightly to fine leg with soft hands on contact",
            "follow_through": "Minimal gentle follow-through guiding ball down to fine leg",
            "recovery": "Smooth reset"
        },
        "hip": [0.06, 0.90, -0.04],
        "leadStride": [0.26, 0.0, -0.10],
        "rearFoot": [-0.14, 0.0, -0.02],
        "handle": [0.14, 0.76, -0.12],
        "batTip": [0.22, 0.26, -0.22],
        "batAngle": 12.0,
        "leadKnee": 136.0,
        "rearKnee": 158.0,
        "leadElbow": 120.0,
        "rearElbow": 102.0,
        "torsoLean": 18.0,
        "torsoSideLean": -4.0,
        "torsoRot": 16.0,
        "ftBatAngle": 22.0,
        "ftBatTip": [0.18, 0.45, -0.26],
        "kneeling": False
    },
    {
        "id": "clip_shot",
        "name": "Clip Shot",
        "slug": "clip-shot",
        "category": "Leg-side and Wrist-oriented Strokes",
        "swingPlane": "angled_leg",
        "ball": {
            "line": "Middle and leg stump",
            "length": "Full / good length",
            "pitch": [0.60, 0.0, -0.12],
            "contact": [0.30, 0.42, -0.10]
        },
        "mistakes": [
            "Playing in front of pad without clear sightline",
            "Hitting across the line before head gets over ball",
            "Weak bottom hand causing mis-timed squirt"
        ],
        "drills": [
            "Square leg clip off front pad from half-volley feeds",
            "Foot clearance drill ensuring front toe points to midwicket",
            "Resistance band wrist acceleration exercise"
        ],
        "cues": {
            "stance": "Level stance, chin tucked toward front shoulder",
            "backlift": "Backlift raised towards off stump",
            "stride": "Front foot steps to pitch of ball, toe pointing to mid-on",
            "downswing": "Bat swings smoothly down the line before snapping wrists",
            "impact": "Crisp clip off the front pad sending ball racing to square leg",
            "follow_through": "Wrists complete rotation, bat finishes near opposite shoulder",
            "recovery": "Balance recovery back to crease"
        },
        "hip": [0.08, 0.89, -0.03],
        "leadStride": [0.34, 0.0, -0.10],
        "rearFoot": [-0.14, 0.0, -0.03],
        "handle": [0.20, 0.74, -0.08],
        "batTip": [0.30, 0.25, -0.15],
        "batAngle": 15.0,
        "leadKnee": 126.0,
        "rearKnee": 158.0,
        "leadElbow": 132.0,
        "rearElbow": 105.0,
        "torsoLean": 22.0,
        "torsoSideLean": -5.0,
        "torsoRot": 25.0,
        "ftBatAngle": -50.0,
        "ftBatTip": [0.20, 1.52, -0.22],
        "kneeling": False
    },
    {
        "id": "sweep",
        "name": "Sweep",
        "slug": "sweep",
        "category": "Sweep-family Strokes",
        "swingPlane": "horizontal",
        "ball": {
            "line": "Middle and leg stump line",
            "length": "Good length spinner pitch",
            "pitch": [0.58, 0.0, -0.08],
            "contact": [0.32, 0.22, -0.12]
        },
        "mistakes": [
            "Not getting rear knee down to turf, leaving body too high",
            "Swinging across the line with top edge toward helmet",
            "Head staying back away from the pitch of the ball"
        ],
        "drills": [
            "Rear knee on turf stationary sweep from bowling machine",
            "High-to-low horizontal ground roll drill",
            "Towel slide lunge drill ensuring low center of mass"
        ],
        "cues": {
            "stance": "Low balanced base anticipating spin trajectory",
            "backlift": "Bat raised high above rear shoulder",
            "stride": "Front foot lunges deep down pitch, rear knee drops to turf",
            "downswing": "Horizontal bat sweeps parallel to ground across the line",
            "impact": "Ball struck well in front of lead pad under nose, blade rolled down",
            "follow_through": "Bat wraps smoothly around front shoulder, rear knee anchored",
            "recovery": "Push off front heel and rise back into stance"
        },
        "hip": [0.22, 0.52, -0.02],
        "leadStride": [0.55, 0.0, -0.08],
        "rearFoot": [-0.18, 0.0, 0.0],
        "handle": [0.26, 0.44, -0.06],
        "batTip": [0.38, 0.18, -0.38],
        "batAngle": 88.0,
        "leadKnee": 95.0,
        "rearKnee": 65.0,
        "leadElbow": 125.0,
        "rearElbow": 115.0,
        "torsoLean": 36.0,
        "torsoSideLean": -6.0,
        "torsoRot": 38.0,
        "ftBatAngle": 140.0,
        "ftBatTip": [0.12, 0.72, -0.42],
        "kneeling": True
    },
    {
        "id": "slog_sweep",
        "name": "Slog Sweep",
        "slug": "slog-sweep",
        "category": "Sweep-family Strokes",
        "swingPlane": "overhead",
        "ball": {
            "line": "Off to middle stump",
            "length": "Full spinner / tossed up",
            "pitch": [0.62, 0.0, 0.04],
            "contact": [0.36, 0.32, -0.06]
        },
        "mistakes": [
            "Hitting purely across without getting under the flight",
            "Pulling head up early to see where the ball travels",
            "Losing knee anchor causing unbalanced swipe"
        ],
        "drills": [
            "Medicine ball kneeling launch over deep midwicket rope",
            "Tossed up spinner boundary clearing drill",
            "Power rotation hold on knee with weighted resistance"
        ],
        "cues": {
            "stance": "Aggressive ready base primed for spin attack",
            "backlift": "Exaggerated high backlift over rear shoulder",
            "stride": "Explosive lunge forward, rear knee close to ground",
            "downswing": "High-velocity upward rotary sweep from beneath ball arc",
            "impact": "Massive strike launching ball high over deep midwicket",
            "follow_through": "Extensive towering follow-through high over lead shoulder",
            "recovery": "Absorb momentum and push up from turf"
        },
        "hip": [0.24, 0.56, 0.0],
        "leadStride": [0.54, 0.0, -0.06],
        "rearFoot": [-0.18, 0.0, 0.02],
        "handle": [0.28, 0.52, -0.02],
        "batTip": [0.42, 0.34, -0.32],
        "batAngle": 62.0,
        "leadKnee": 102.0,
        "rearKnee": 72.0,
        "leadElbow": 145.0,
        "rearElbow": 135.0,
        "torsoLean": 30.0,
        "torsoSideLean": -4.0,
        "torsoRot": 45.0,
        "ftBatAngle": 160.0,
        "ftBatTip": [0.18, 1.45, -0.36],
        "kneeling": True
    },
    {
        "id": "reverse_sweep",
        "name": "Reverse Sweep",
        "slug": "reverse-sweep",
        "category": "Sweep-family Strokes",
        "swingPlane": "horizontal",
        "ball": {
            "line": "Leg stump to middle stump",
            "length": "Good length spinner drifting in",
            "pitch": [0.56, 0.0, -0.12],
            "contact": [0.30, 0.24, 0.16]
        },
        "mistakes": [
            "Failing to switch hands or flip bat face cleanly",
            "Swinging blindly without watching ball impact the blade",
            "Exposing stumps while missing line entirely"
        ],
        "drills": [
            "Grip swap transition drill off stationary tee",
            "Off-side target funnel past backward point",
            "Underarm feed reverse contact under eye-line"
        ],
        "cues": {
            "stance": "Conventional stance that swiftly initiates grip switch",
            "backlift": "Hands cross over, reversing blade face toward off side",
            "stride": "Front foot steps towards off side, rear knee sinks to turf",
            "downswing": "Bat sweeps horizontally across body toward third man/point",
            "impact": "Clean reverse contact deflecting ball through vacant off side",
            "follow_through": "Blade wraps around right shoulder on off-side finish",
            "recovery": "Reset hands and return to batting stance"
        },
        "hip": [0.20, 0.54, 0.04],
        "leadStride": [0.52, 0.0, 0.10],
        "rearFoot": [-0.16, 0.0, -0.04],
        "handle": [0.24, 0.46, 0.08],
        "batTip": [0.36, 0.20, 0.38],
        "batAngle": -82.0,
        "leadKnee": 98.0,
        "rearKnee": 68.0,
        "leadElbow": 120.0,
        "rearElbow": 118.0,
        "torsoLean": 32.0,
        "torsoSideLean": 12.0,
        "torsoRot": -35.0,
        "ftBatAngle": -140.0,
        "ftBatTip": [0.10, 0.75, 0.44],
        "kneeling": True
    },
    {
        "id": "paddle_sweep",
        "name": "Paddle Sweep",
        "slug": "paddle-sweep",
        "category": "Sweep-family Strokes",
        "swingPlane": "horizontal",
        "ball": {
            "line": "Leg stump corridor",
            "length": "Full / yorker length on leg line",
            "pitch": [0.60, 0.0, -0.16],
            "contact": [0.34, 0.20, -0.22]
        },
        "mistakes": [
            "Hitting the ball hard instead of gently paddling pace",
            "Paddle angle too straight sending ball back to bowler",
            "Leaving gap between bat and front pad for ball to penetrate"
        ],
        "drills": [
            "Fine leg bucket deflection drill from low kneeling pose",
            "Soft hands tennis ball touch behind wicketkeeper",
            "Paddle sweep target grid inside boundary marker"
        ],
        "cues": {
            "stance": "Low ready base waiting for full leg-stump delivery",
            "backlift": "Controlled lift, hands positioned high in front",
            "stride": "Front leg strides forward, rear knee drops softly",
            "downswing": "Horizontal blade guides path softly along ground line",
            "impact": "Feather touch paddling pace fine past short fine leg",
            "follow_through": "Soft extension toward fine leg without wild follow-through",
            "recovery": "Steady stance reset"
        },
        "hip": [0.20, 0.53, -0.04],
        "leadStride": [0.54, 0.0, -0.12],
        "rearFoot": [-0.16, 0.0, -0.02],
        "handle": [0.26, 0.42, -0.10],
        "batTip": [0.38, 0.16, -0.32],
        "batAngle": 72.0,
        "leadKnee": 96.0,
        "rearKnee": 66.0,
        "leadElbow": 118.0,
        "rearElbow": 105.0,
        "torsoLean": 34.0,
        "torsoSideLean": -6.0,
        "torsoRot": 28.0,
        "ftBatAngle": 85.0,
        "ftBatTip": [0.28, 0.32, -0.36],
        "kneeling": True
    },
    {
        "id": "slog",
        "name": "Slog",
        "slug": "slog",
        "category": "Power and Innovative Shots",
        "swingPlane": "overhead",
        "ball": {
            "line": "Middle stump",
            "length": "Good / length ball looking to clear rope",
            "pitch": [0.55, 0.0, 0.0],
            "contact": [0.30, 0.45, -0.10]
        },
        "mistakes": [
            "Swinging across the line with head tilted away from ball",
            "Clearing front leg so far that balance is completely destroyed",
            "Bottom hand over-rotating into a top edge skyer"
        ],
        "drills": [
            "Clear front leg rotational drive with heavy training bat",
            "Over-the-boundary power clearance off batting tee",
            "Hip coil and release exercise with resistance band"
        ],
        "cues": {
            "stance": "Wide power stance, low center of gravity",
            "backlift": "Massive backlift winding up past right ear",
            "stride": "Front leg clears slightly to leg side to open hip rotation",
            "downswing": "Violent full-blooded rotary swing across the line",
            "impact": "Explosive contact launching ball high over cow corner",
            "follow_through": "Full-body wrap around shoulders with head steady",
            "recovery": "Staggered balance check and return"
        },
        "hip": [0.10, 0.88, -0.06],
        "leadStride": [0.36, 0.0, -0.22],
        "rearFoot": [-0.16, 0.0, 0.0],
        "handle": [0.20, 0.82, -0.06],
        "batTip": [0.32, 0.42, -0.36],
        "batAngle": 75.0,
        "leadKnee": 132.0,
        "rearKnee": 140.0,
        "leadElbow": 145.0,
        "rearElbow": 135.0,
        "torsoLean": 16.0,
        "torsoSideLean": -8.0,
        "torsoRot": 48.0,
        "ftBatAngle": 165.0,
        "ftBatTip": [-0.05, 1.62, -0.40],
        "kneeling": False
    },
    {
        "id": "switch_hit",
        "name": "Switch Hit",
        "slug": "switch-hit",
        "category": "Power and Innovative Shots",
        "swingPlane": "angled_off",
        "ball": {
            "line": "Full ball outside off stump",
            "length": "Full / slot delivery",
            "pitch": [0.65, 0.0, 0.20],
            "contact": [0.36, 0.40, 0.22]
        },
        "mistakes": [
            "Switching feet too early giving away intention to bowler",
            "Clumsy foot swap tripping up and losing base",
            "Poor grip transition resulting in weak mishit"
        ],
        "drills": [
            "Foot swap jump transition drill without bat on agility ladder",
            "Opposite hand shadow swing off batting tee",
            "Reaction feed switch hit against slow bowling machine"
        ],
        "cues": {
            "stance": "Right-hand stance until bowler enters delivery stride",
            "backlift": "Swiftly jump-swap feet and hands into left-handed stance",
            "stride": "Step out as a natural southpaw toward extra cover",
            "downswing": "Unleash powerful drive through off side as a left-hander",
            "impact": "Clean middle of the bat striking over extra cover boundary",
            "follow_through": "High elegant left-handed finish across right shoulder",
            "recovery": "Reset feet to natural stance"
        },
        "hip": [0.12, 0.88, 0.10],
        "leadStride": [0.42, 0.0, 0.25],
        "rearFoot": [-0.15, 0.0, -0.02],
        "handle": [0.24, 0.78, 0.20],
        "batTip": [0.36, 0.25, 0.26],
        "batAngle": 20.0,
        "leadKnee": 122.0,
        "rearKnee": 155.0,
        "leadElbow": 138.0,
        "rearElbow": 95.0,
        "torsoLean": 25.0,
        "torsoSideLean": 14.0,
        "torsoRot": -22.0,
        "ftBatAngle": -78.0,
        "ftBatTip": [0.28, 1.75, 0.35],
        "kneeling": False
    },
    {
        "id": "scoop_shot",
        "name": "Scoop Shot",
        "slug": "scoop-shot",
        "category": "Power and Innovative Shots",
        "swingPlane": "ramp",
        "ball": {
            "line": "Middle to off stump",
            "length": "Full yorker or low full toss",
            "pitch": [0.68, 0.0, 0.02],
            "contact": [0.30, 0.25, 0.0]
        },
        "mistakes": [
            "Failing to get eyes down low level with the ball trajectory",
            "Scooping too late leading to impact directly on helmet grill",
            "Bat face angled flat instead of tilted upward ramp"
        ],
        "drills": [
            "Deep squat ramp drill off bowling machine into target behind keeper",
            "Soft safety-ball scoop reaction test with full head protection",
            "Knee drop angle positioning drill on turf"
        ],
        "cues": {
            "stance": "Dynamic stance looking for yorker delivery length",
            "backlift": "Drop low into deep crouch beneath ball flight line",
            "stride": "Front foot steps forward, knees deeply flexed close to ground",
            "downswing": "Bat held flat underneath ball face pointing upward like a ramp",
            "impact": "Ball deflects off upward ramp blade cleanly over keeper's head",
            "follow_through": "Arms elevate straight upward guiding ball trajectory",
            "recovery": "Push up from squat into upright balance"
        },
        "hip": [0.12, 0.58, 0.0],
        "leadStride": [0.42, 0.0, 0.02],
        "rearFoot": [-0.14, 0.0, -0.02],
        "handle": [0.22, 0.38, 0.02],
        "batTip": [0.32, 0.20, 0.0],
        "batAngle": 115.0,
        "leadKnee": 88.0,
        "rearKnee": 82.0,
        "leadElbow": 130.0,
        "rearElbow": 125.0,
        "torsoLean": 38.0,
        "torsoSideLean": 0.0,
        "torsoRot": 0.0,
        "ftBatAngle": 135.0,
        "ftBatTip": [0.20, 0.85, 0.02],
        "kneeling": False
    },
    {
        "id": "ramp_shot",
        "name": "Ramp Shot",
        "slug": "ramp-shot",
        "category": "Power and Innovative Shots",
        "swingPlane": "ramp",
        "ball": {
            "line": "Outside off stump corridor",
            "length": "Good length / short of length with pace",
            "pitch": [0.52, 0.0, 0.22],
            "contact": [0.15, 0.50, 0.20]
        },
        "mistakes": [
            "Ramping without judging bounce, resulting in edge to slips",
            "Hands too stiff absorbing impact rather than angling pace",
            "Exposing all three stumps without securing contact line"
        ],
        "drills": [
            "Pace redirection drill over fine leg / third man nets",
            "Soft wrist deflector drill using reaction balls",
            "Shuffle across crease ramp simulation"
        ],
        "cues": {
            "stance": "Side-on stance ready to shuffle across",
            "backlift": "Bat raised early with open blade facing backward",
            "stride": "Shuffle across toward off stump, getting inside the line",
            "downswing": "Angle the bat face deliberately toward fine leg / third man",
            "impact": "Use bowler's express pace to ramp ball over slips / keeper",
            "follow_through": "Controlled touch finish without excessive arm swing",
            "recovery": "Step back to crease center"
        },
        "hip": [0.08, 0.72, 0.08],
        "leadStride": [0.28, 0.0, 0.12],
        "rearFoot": [-0.12, 0.0, 0.04],
        "handle": [0.14, 0.56, 0.14],
        "batTip": [0.22, 0.32, 0.22],
        "batAngle": 78.0,
        "leadKnee": 110.0,
        "rearKnee": 118.0,
        "leadElbow": 122.0,
        "rearElbow": 115.0,
        "torsoLean": 26.0,
        "torsoSideLean": 8.0,
        "torsoRot": -12.0,
        "ftBatAngle": 92.0,
        "ftBatTip": [0.12, 0.78, 0.24],
        "kneeling": False
    },
    {
        "id": "helicopter_shot",
        "name": "Helicopter Shot",
        "slug": "helicopter-shot",
        "category": "Power and Innovative Shots",
        "swingPlane": "overhead",
        "ball": {
            "line": "Middle and leg yorker",
            "length": "Toe-crushing yorker on batting crease",
            "pitch": [0.72, 0.0, -0.06],
            "contact": [0.38, 0.20, -0.04]
        },
        "mistakes": [
            "Trying to flick with top hand rather than explosive bottom hand wrist snap",
            "Not digging the yorker out out in front of the toes",
            "Stopping the follow-through early causing severe wrist strain"
        ],
        "drills": [
            "Yorker blockhole power flick off rubber base",
            "360-degree overhead bat rotation wrist mobility drill",
            "Heavy wrist curl strengthening and medicine ball rotational throw"
        ],
        "cues": {
            "stance": "Solid grounded stance braced for high-pace yorker",
            "backlift": "High powerful backlift wound up like a spring",
            "stride": "Firm front-foot plant digging bat down right at the blockhole",
            "downswing": "Violent downward descent into toe line with pure bottom hand power",
            "impact": "Immense bottom-hand wrist flick digging yorker high into midwicket night sky",
            "follow_through": "Bat whirls in a 360-degree overhead helicopter loop across shoulders",
            "recovery": "Controlled landing holding ground after circular finish"
        },
        "hip": [0.14, 0.82, -0.02],
        "leadStride": [0.44, 0.0, -0.06],
        "rearFoot": [-0.15, 0.0, -0.02],
        "handle": [0.26, 0.62, -0.04],
        "batTip": [0.38, 0.16, -0.06],
        "batAngle": 22.0,
        "leadKnee": 112.0,
        "rearKnee": 142.0,
        "leadElbow": 148.0,
        "rearElbow": 138.0,
        "torsoLean": 28.0,
        "torsoSideLean": -4.0,
        "torsoRot": 36.0,
        "ftBatAngle": -160.0,
        "ftBatTip": [-0.10, 1.88, -0.15],
        "kneeling": False
    }
]

def build_phase_keyframe(shot, phase_name, p_idx):
    weights = [1.0, 0.8, 0.85, 0.45, 0.35, 1.15, 0.90]
    weight = weights[p_idx]
    cue = shot["cues"][phase_name]

    # Stance defaults
    st_hip = [0.0, 0.92, 0.0]
    st_lead_foot = [0.20, 0.0, 0.0]
    st_rear_foot = [-0.15, 0.0, -0.05]
    st_bat_handle = [0.02, 0.82, 0.0]
    st_bat_tip = [0.08, 0.12, 0.0]
    st_lead_wrist = [0.04, 0.82, 0.02]
    st_rear_wrist = [0.0, 0.82, -0.02]

    imp_hip = shot["hip"]
    imp_lead_foot = shot["leadStride"]
    imp_rear_foot = shot["rearFoot"]
    imp_handle = shot["handle"]
    imp_tip = shot["batTip"]
    imp_bat_angle = shot["batAngle"]
    imp_lead_knee = shot["leadKnee"]
    imp_rear_knee = shot["rearKnee"]
    imp_lead_elbow = shot["leadElbow"]
    imp_rear_elbow = shot["rearElbow"]
    imp_torso_lean = shot["torsoLean"]
    imp_torso_side = shot["torsoSideLean"]
    imp_torso_rot = shot["torsoRot"]

    ft_bat_angle = shot["ftBatAngle"]
    ft_tip = shot["ftBatTip"]
    is_kneeling = shot["kneeling"]

    # Interpolation factors across 7 phases (0..6)
    if p_idx == 0:  # Stance
        hip = st_hip
        lead_foot = st_lead_foot
        rear_foot = st_rear_foot
        lead_knee = 162.0; rear_knee = 160.0
        lead_elbow = 100.0; rear_elbow = 105.0
        torso_lean = 14.0; torso_side = 0.0; torso_rot = 0.0
        bat_angle = 20.0
        handle = st_bat_handle
        tip = st_bat_tip
        lead_wrist = st_lead_wrist
        rear_wrist = st_rear_wrist
        over_knee = False
        kneeling_rear = False

    elif p_idx == 1:  # Backlift
        hip = [st_hip[0] - 0.04, st_hip[1] - 0.02, st_hip[2]]
        lead_foot = st_lead_foot
        rear_foot = st_rear_foot
        lead_knee = 165.0; rear_knee = 155.0
        lead_elbow = 110.0; rear_elbow = 80.0
        torso_lean = 12.0; torso_side = 2.0; torso_rot = -10.0
        bat_angle = -50.0
        handle = [-0.08, 1.05, 0.12]
        tip = [-0.22, 1.62, 0.28]
        lead_wrist = [-0.06, 1.05, 0.14]
        rear_wrist = [-0.10, 1.05, 0.10]
        over_knee = False
        kneeling_rear = False

    elif p_idx == 2:  # Stride
        hip = [st_hip[0] + (imp_hip[0] - st_hip[0]) * 0.7, st_hip[1] + (imp_hip[1] - st_hip[1]) * 0.6, imp_hip[2] * 0.7]
        lead_foot = [st_lead_foot[0] + (imp_lead_foot[0] - st_lead_foot[0]) * 0.85, 0.0, imp_lead_foot[2] * 0.85]
        rear_foot = imp_rear_foot
        lead_knee = 162.0 + (imp_lead_knee - 162.0) * 0.6
        rear_knee = 160.0 + (imp_rear_knee - 160.0) * 0.5
        lead_elbow = 110.0 + (imp_lead_elbow - 110.0) * 0.4
        rear_elbow = 95.0
        torso_lean = 14.0 + (imp_torso_lean - 14.0) * 0.6
        torso_side = imp_torso_side * 0.6
        torso_rot = imp_torso_rot * 0.5
        bat_angle = -25.0
        handle = [-0.02, 1.08, imp_handle[2] * 0.5]
        tip = [-0.12, 1.68, imp_tip[2] * 0.5]
        lead_wrist = [0.0, 1.08, imp_handle[2] * 0.5 + 0.02]
        rear_wrist = [-0.04, 1.08, imp_handle[2] * 0.5 - 0.02]
        over_knee = imp_lead_foot[0] > 0.35 and not is_kneeling
        kneeling_rear = False

    elif p_idx == 3:  # Downswing
        hip = [imp_hip[0] * 0.9, imp_hip[1] * 0.95, imp_hip[2] * 0.9]
        lead_foot = imp_lead_foot
        rear_foot = imp_rear_foot
        lead_knee = 162.0 + (imp_lead_knee - 162.0) * 0.85
        rear_knee = 160.0 + (imp_rear_knee - 160.0) * 0.8
        lead_elbow = imp_lead_elbow
        rear_elbow = imp_rear_elbow
        torso_lean = imp_torso_lean * 0.85
        torso_side = imp_torso_side * 0.85
        torso_rot = imp_torso_rot * 0.8
        bat_angle = imp_bat_angle * 0.5
        handle = [imp_handle[0] - 0.08, imp_handle[1] + 0.15, imp_handle[2] * 0.8]
        tip = [imp_tip[0] - 0.15, imp_tip[1] + 0.35, imp_tip[2] * 0.8]
        lead_wrist = [handle[0] + 0.02, handle[1], handle[2] + 0.02]
        rear_wrist = [handle[0] - 0.02, handle[1], handle[2] - 0.02]
        over_knee = imp_lead_foot[0] > 0.35
        kneeling_rear = is_kneeling

    elif p_idx == 4:  # Impact (Authentic per-shot authored values)
        hip = imp_hip
        lead_foot = imp_lead_foot
        rear_foot = imp_rear_foot
        lead_knee = imp_lead_knee
        rear_knee = imp_rear_knee
        lead_elbow = imp_lead_elbow
        rear_elbow = imp_rear_elbow
        torso_lean = imp_torso_lean
        torso_side = imp_torso_side
        torso_rot = imp_torso_rot
        bat_angle = imp_bat_angle
        handle = imp_handle
        tip = imp_tip
        lead_wrist = [handle[0] + 0.02, handle[1], handle[2] + 0.02]
        rear_wrist = [handle[0] - 0.02, handle[1], handle[2] - 0.02]
        over_knee = (imp_lead_foot[0] > 0.35) and (not is_kneeling or p_idx == 4)
        kneeling_rear = is_kneeling

    elif p_idx == 5:  # Follow-through
        hip = [imp_hip[0] + 0.02, imp_hip[1] + 0.02, imp_hip[2]]
        lead_foot = imp_lead_foot
        rear_foot = imp_rear_foot
        lead_knee = imp_lead_knee + 4.0
        rear_knee = imp_rear_knee + 2.0
        lead_elbow = imp_lead_elbow + 15.0
        rear_elbow = imp_rear_elbow + 10.0
        torso_lean = max(8.0, imp_torso_lean - 4.0)
        torso_side = imp_torso_side * 0.8
        torso_rot = imp_torso_rot * 1.2
        bat_angle = ft_bat_angle
        handle = [ft_tip[0] - 0.12, ft_tip[1] - 0.55, ft_tip[2] * 0.7]
        tip = ft_tip
        lead_wrist = [handle[0] + 0.03, handle[1], handle[2] + 0.02]
        rear_wrist = [handle[0] - 0.03, handle[1], handle[2] - 0.02]
        over_knee = imp_lead_foot[0] > 0.35
        kneeling_rear = is_kneeling

    else:  # Recovery
        hip = [st_hip[0] + 0.05, st_hip[1] - 0.02, 0.0]
        lead_foot = [st_lead_foot[0] + 0.08, 0.0, 0.0]
        rear_foot = st_rear_foot
        lead_knee = 150.0; rear_knee = 152.0
        lead_elbow = 105.0; rear_elbow = 110.0
        torso_lean = 16.0; torso_side = 0.0; torso_rot = 0.0
        bat_angle = 30.0
        handle = [0.06, 0.78, 0.02]
        tip = [0.12, 0.18, 0.02]
        lead_wrist = [0.08, 0.78, 0.04]
        rear_wrist = [0.04, 0.78, 0.0]
        over_knee = False
        kneeling_rear = False

    # Chest & Head positions via forward kinematics
    chest_y = hip[1] + 0.42 * (1.0 - torso_lean * 0.003)
    chest_x = hip[0] + 0.38 * (torso_lean / 90.0)
    chest_z = hip[2] + 0.15 * (torso_side / 90.0)
    chest = [round(chest_x, 3), round(chest_y, 3), round(chest_z, 3)]

    head_x = chest[0] + 0.18 * (torso_lean / 90.0)
    head_y = chest[1] + 0.26
    head_z = chest[2] + 0.08 * (torso_side / 90.0)
    head = {
        "x": round(head_x, 3),
        "y": round(head_y, 3),
        "z": round(head_z, 3),
        "tiltDeg": round(torso_lean * 0.3, 1),
        "overFrontKnee": over_knee
    }

    # Shoulder positions
    sh_span = 0.36
    lead_sh = [round(chest[0] + 0.04, 3), round(chest[1] + 0.02, 3), round(chest[2] + sh_span * 0.5, 3)]
    rear_sh = [round(chest[0] - 0.04, 3), round(chest[1] + 0.02, 3), round(chest[2] - sh_span * 0.5, 3)]

    # Elbow joint positions
    lead_el = [
        round((lead_sh[0] + lead_wrist[0]) / 2 + 0.08, 3),
        round((lead_sh[1] + lead_wrist[1]) / 2 + 0.04, 3),
        round((lead_sh[2] + lead_wrist[2]) / 2 + 0.04, 3)
    ]
    rear_el = [
        round((rear_sh[0] + rear_wrist[0]) / 2 - 0.04, 3),
        round((rear_sh[1] + rear_wrist[1]) / 2 - 0.04, 3),
        round((rear_sh[2] + rear_wrist[2]) / 2 - 0.04, 3)
    ]

    # Knee positions
    lead_knee_y = (hip[1] + lead_foot[1]) / 2
    if is_kneeling and p_idx >= 3:
        rear_knee_y = 0.08
    else:
        rear_knee_y = (hip[1] + rear_foot[1]) / 2

    lead_knee_pt = [round((hip[0] + lead_foot[0]) / 2 + 0.05, 3), round(lead_knee_y, 3), round(lead_foot[2], 3)]
    rear_knee_pt = [round((hip[0] + rear_foot[0]) / 2 - 0.04, 3), round(rear_knee_y, 3), round(rear_foot[2], 3)]

    points = [
        f"Head aligned over front knee: {'Yes' if over_knee else 'Anchored'}",
        f"Lead knee flexion target: {int(lead_knee)}°",
        f"Bat path plane: {shot['swingPlane']}",
        f"Torso lean forward: {int(torso_lean)}°"
    ]

    return {
        "phaseKey": phase_name,
        "label": f"{p_idx + 1}. {phase_name.replace('_', ' ').title()}",
        "durationWeight": weight,
        "cue": cue,
        "techniquePoints": points,
        "head": head,
        "torso": {
            "leanDeg": round(torso_lean, 1),
            "sideLeanDeg": round(torso_side, 1),
            "rotationDeg": round(torso_rot, 1),
            "hip": [round(hip[0], 3), round(hip[1], 3), round(hip[2], 3)],
            "chest": chest
        },
        "leadLeg": {
            "hipAngleDeg": round(180.0 - lead_knee * 0.5, 1),
            "kneeAngleDeg": round(lead_knee, 1),
            "ankleAngleDeg": round(80.0 + (180.0 - lead_knee) * 0.2, 1),
            "kneePos": lead_knee_pt,
            "footPos": [round(lead_foot[0], 3), round(lead_foot[1], 3), round(lead_foot[2], 3)],
            "isKneeling": False
        },
        "rearLeg": {
            "hipAngleDeg": round(180.0 - rear_knee * 0.5, 1),
            "kneeAngleDeg": round(rear_knee, 1),
            "ankleAngleDeg": round(80.0 + (180.0 - rear_knee) * 0.2, 1),
            "kneePos": rear_knee_pt,
            "footPos": [round(rear_foot[0], 3), round(rear_foot[1], 3), round(rear_foot[2], 3)],
            "isKneeling": kneeling_rear
        },
        "leadArm": {
            "shoulderPos": lead_sh,
            "elbowPos": lead_el,
            "elbowAngleDeg": round(lead_elbow, 1),
            "wristPos": [round(lead_wrist[0], 3), round(lead_wrist[1], 3), round(lead_wrist[2], 3)]
        },
        "rearArm": {
            "shoulderPos": rear_sh,
            "elbowPos": rear_el,
            "elbowAngleDeg": round(rear_elbow, 1),
            "wristPos": [round(rear_wrist[0], 3), round(rear_wrist[1], 3), round(rear_wrist[2], 3)]
        },
        "bat": {
            "angleDeg": round(bat_angle, 1),
            "bladeFaceDeg": round(imp_torso_rot, 1),
            "handlePos": [round(handle[0], 3), round(handle[1], 3), round(handle[2], 3)],
            "tipPos": [round(tip[0], 3), round(tip[1], 3), round(tip[2], 3)],
            "swingPlane": shot["swingPlane"]
        }
    }

phase_names = ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]

shots_dict = {}
for s in SHOTS:
    phases_dict = {}
    for idx, p_name in enumerate(phase_names):
        phases_dict[p_name] = build_phase_keyframe(s, p_name, idx)

    shots_dict[s["name"]] = {
        "id": s["id"],
        "name": s["name"],
        "slug": s["slug"],
        "category": s["category"],
        "provenance": "authored baseline (tunable)",
        "ballTrajectory": s["ball"],
        "swingPlane": s["swingPlane"],
        "commonMistakes": s["mistakes"],
        "drills": s["drills"],
        "phases": phases_dict
    }

ts_content = f"""/**
 * CricketIQ — Authored 3D Biomechanical Shot Animations
 * Single authoritative source of truth for 3D animation keyframes across all 25 catalogue cricket shots.
 * Provenance: "authored baseline (tunable)".
 * Do not claim measured provenance.
 */

export type SwingPlaneType =
  | 'vertical'
  | 'horizontal'
  | 'angled_off'
  | 'angled_leg'
  | 'overhead'
  | 'ramp';

export interface BallTrajectoryInfo {{
  line: string;
  length: string;
  pitch: [number, number, number];
  contact: [number, number, number];
}}

export interface PhaseKeyframe {{
  phaseKey: 'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery';
  label: string;
  durationWeight: number;
  cue: string;
  techniquePoints: string[];
  head: {{
    x: number;
    y: number;
    z: number;
    tiltDeg: number;
    overFrontKnee: boolean;
  }};
  torso: {{
    leanDeg: number;
    sideLeanDeg: number;
    rotationDeg: number;
    hip: [number, number, number];
    chest: [number, number, number];
  }};
  leadLeg: {{
    hipAngleDeg: number;
    kneeAngleDeg: number;
    ankleAngleDeg: number;
    kneePos: [number, number, number];
    footPos: [number, number, number];
    isKneeling: boolean;
  }};
  rearLeg: {{
    hipAngleDeg: number;
    kneeAngleDeg: number;
    ankleAngleDeg: number;
    kneePos: [number, number, number];
    footPos: [number, number, number];
    isKneeling: boolean;
  }};
  leadArm: {{
    shoulderPos: [number, number, number];
    elbowPos: [number, number, number];
    elbowAngleDeg: number;
    wristPos: [number, number, number];
  }};
  rearArm: {{
    shoulderPos: [number, number, number];
    elbowPos: [number, number, number];
    elbowAngleDeg: number;
    wristPos: [number, number, number];
  }};
  bat: {{
    angleDeg: number;
    bladeFaceDeg: number;
    handlePos: [number, number, number];
    tipPos: [number, number, number];
    swingPlane: SwingPlaneType;
  }};
}}

export interface ShotAnimationDefinition {{
  id: string;
  name: string;
  slug: string;
  category: string;
  provenance: string;
  ballTrajectory: BallTrajectoryInfo;
  swingPlane: SwingPlaneType;
  commonMistakes: string[];
  drills: string[];
  phases: Record<string, PhaseKeyframe>;
}}

export const SHOT_ANIMATIONS: Record<string, ShotAnimationDefinition> = {json.dumps(shots_dict, indent=2)};

export function getShotAnimation(idOrName: string): ShotAnimationDefinition {{
  if (!idOrName) return SHOT_ANIMATIONS['Cover Drive'];
  const n = idOrName.trim().toLowerCase();

  // Match by exact key name
  for (const [k, v] of Object.entries(SHOT_ANIMATIONS)) {{
    if (k.toLowerCase() === n) return v;
  }}
  // Match by id or slug
  for (const v of Object.values(SHOT_ANIMATIONS)) {{
    if (v.id.toLowerCase() === n || v.slug.toLowerCase() === n || v.slug.toLowerCase() === n.replace(/\\s+/g, '-')) {{
      return v;
    }}
  }}
  // Substring fallback
  for (const [k, v] of Object.entries(SHOT_ANIMATIONS)) {{
    if (k.toLowerCase().includes(n) || n.includes(k.toLowerCase())) return v;
  }}
  return SHOT_ANIMATIONS['Cover Drive'];
}}

export function getAllShotAnimations(): ShotAnimationDefinition[] {{
  return Object.values(SHOT_ANIMATIONS);
}}
"""

out_file = Path("frontend/src/data/shotAnimations.ts")
out_file.write_text(ts_content, encoding="utf-8")
print(f"Successfully generated {out_file} with {len(shots_dict)} shots!")
