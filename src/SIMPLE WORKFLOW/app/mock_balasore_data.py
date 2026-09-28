import io
from pathlib import Path
from PIL import Image, ImageDraw
from app.config import UPLOAD_DIR
from app.schemas import AnteMortemProfile, PostMortemRecord
from app.database import get_dvi_db

def generate_evidence_photo(filename: str, bg_color, garment_color, mark_label: str) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    img_path = UPLOAD_DIR / filename
    
    img = Image.new("RGB", (300, 300), color=bg_color)
    draw = ImageDraw.Draw(img)
    # Silhouette
    draw.ellipse([90, 40, 210, 160], fill=(235, 195, 170))
    # Garment / torso
    draw.rectangle([50, 170, 250, 300], fill=garment_color)
    # Distinctive marker hint
    draw.text((20, 260), mark_label[:32], fill=(255, 255, 255))

    img.save(img_path, format="JPEG")
    return f"/static/uploads/{filename}"

def seed_balasore_dataset():
    db = get_dvi_db()
    existing_am = db.get_all_am()
    if len(existing_am) >= 3:
        print("Balasore dataset already seeded.")
        return

    print("Seeding realistic Odisha Balasore train collision DVI dataset...")

    # Photos
    p1_am = generate_evidence_photo("am_subrata_1.jpg", (240, 240, 240), (140, 30, 30), "Subrata Sen - Family Photo")
    p1_pm = generate_evidence_photo("pm_bal_042.jpg", (220, 220, 220), (130, 25, 25), "PM-042 Coach B4 Body")

    p2_am = generate_evidence_photo("am_priya_1.jpg", (245, 240, 245), (30, 80, 180), "Priya Sharma - Family Photo")
    p2_pm = generate_evidence_photo("pm_bal_109.jpg", (230, 230, 230), (25, 75, 170), "PM-109 Coach S1 Body")

    p3_am = generate_evidence_photo("am_rajesh_1.jpg", (235, 245, 240), (20, 120, 40), "Rajesh Soren - Family Photo")
    p3_pm = generate_evidence_photo("pm_bal_187.jpg", (225, 225, 225), (20, 115, 35), "PM-187 Track Km 254 Body")

    # 1. AM Profile: Subrata Sen (Passenger on Coromandel Coach B4)
    am1 = AnteMortemProfile(
        id="AM-BAL-014",
        custom_id="AM-BAL-014",
        full_name="Subrata Sen",
        reported_by="Debabrata Sen (Brother, Kolkata)",
        contact_phone="+91 98301 XXXXX",
        gender="Male",
        age=32,
        age_range="30-35",
        height_cm=172.0,
        hair_description="Short black wavy hair, clean-shaven",
        scars_and_birthmarks="Surgical appendectomy scar right lower abdomen, small dark mole on left cheek",
        tattoos_piercings="No visible tattoos",
        clothing_worn="Maroon printed cotton kurta, beige trousers, brown leather wristwatch",
        jewelry_accessories="Silver finger ring with blue sapphire stone on right hand index finger, red kalawa sacred thread",
        dental_notes="Missing upper right second premolar (#14), visible white ceramic crown on lower right first molar (#30)",
        other_observations="Blood group B+, had wallet with WB Aadhaar card",
        image_paths=[p1_am],
        created_at="2023-06-03T09:15:00",
        status="Active_Searching"
    )

    # 2. PM Record: Body recovered from Balasore Coach B4 (Matches Subrata Sen)
    pm1 = PostMortemRecord(
        id="PM-BAL-042",
        custom_id="PM-BAL-042",
        recovery_location="Coromandel Express Coach B4, Compartment 3, Track km 254.2",
        mortuary_facility="AIIMS Bhubaneswar Cold Unit #4",
        estimated_gender="Male",
        estimated_age_range="28-36",
        estimated_height_cm=171.0,
        hair_observation="Black wavy hair approx 5cm, light facial stubble",
        scars_and_birthmarks="Well-healed surgical appendectomy scar (approx 5cm) in right iliac fossa; pigmented nevus (mole) left zygomatic cheek region",
        tattoos_piercings="None observed on extremities",
        clothing_recovered="Shreds of maroon printed ethnic kurta, beige synthetic blend trousers",
        jewelry_belongings="White metal/silver ring with oval blue gem on right second digit; red cotton religious thread on wrist",
        dental_observations="Antemortem absence of tooth #14; intact white crown restoration on tooth #30",
        pathology_notes="Blunt chest trauma consistent with derailment impact; facial features partially intact",
        image_paths=[p1_pm],
        created_at="2023-06-03T14:30:00",
        status="Unidentified"
    )

    # 3. AM Profile: Priya Sharma
    am2 = AnteMortemProfile(
        id="AM-BAL-055",
        custom_id="AM-BAL-055",
        full_name="Priya Sharma",
        reported_by="Anand Sharma (Husband, Cuttack)",
        contact_phone="+91 94370 XXXXX",
        gender="Female",
        age=27,
        age_range="25-30",
        height_cm=158.0,
        hair_description="Long dark brown hair, tied in braid",
        scars_and_birthmarks="Linear burn scar on inner left forearm (cooking oil splash)",
        tattoos_piercings="Pierced earlobes, small flower tattoo on right wrist",
        clothing_worn="Navy blue churidar suit with floral embroidery, silver payal (anklets)",
        jewelry_accessories="Gold wedding mangalsutra, gold bangles on both wrists",
        dental_notes="All teeth intact, slight overlap of lower incisors",
        other_observations="Blood group O+",
        image_paths=[p2_am],
        created_at="2023-06-03T11:20:00",
        status="Active_Searching"
    )

    # 4. PM Record: Body recovered from Coach S1 (Matches Priya Sharma)
    pm2 = PostMortemRecord(
        id="PM-BAL-109",
        custom_id="PM-BAL-109",
        recovery_location="Howrah Express Coach S1, Berths 45-48 debris",
        mortuary_facility="Balasore District Headquarter Hospital",
        estimated_gender="Female",
        estimated_age_range="25-30",
        estimated_height_cm=157.0,
        hair_observation="Dark brown long hair in braided arrangement",
        scars_and_birthmarks="Old irregular burn scar on ventral aspect of left forearm",
        tattoos_piercings="Punctured earlobes bilaterally, faded floral motif tattoo on dorsal right wrist",
        clothing_recovered="Navy blue embroidered cotton garment fabric remnants",
        jewelry_belongings="Yellow metal ornamental chain with black beads (mangalsutra), two gold-toned wrist bangles",
        dental_observations="Complete dentition, slight crowding/overlap of teeth #24-#26",
        pathology_notes="Polytrauma with head lacerations",
        image_paths=[p2_pm],
        created_at="2023-06-03T18:00:00",
        status="Unidentified"
    )

    # 5. AM Profile: Rajesh Soren
    am3 = AnteMortemProfile(
        id="AM-BAL-089",
        custom_id="AM-BAL-089",
        full_name="Rajesh Soren",
        reported_by="Sunil Soren (Cousin, Balasore)",
        contact_phone="+91 82490 XXXXX",
        gender="Male",
        age=45,
        age_range="40-50",
        height_cm=165.0,
        hair_description="Short black hair with prominent silver/gray patches around temples",
        scars_and_birthmarks="Large dark birthmark behind right ear, healed fracture scar left wrist",
        tattoos_piercings="Trishul tattoo on right forearm with name initial 'R'",
        clothing_worn="Dark green cotton shirt, black jeans, steel wrist kada",
        jewelry_accessories="Stainless steel wrist kada on right arm, black thread around ankle",
        dental_notes="Wears partial removable denture for upper incisors",
        other_observations="Steel kada engraved on inside",
        image_paths=[p3_am],
        created_at="2023-06-03T16:45:00",
        status="Active_Searching"
    )

    # 6. PM Record: Body recovered at Track Km 254 (Matches Rajesh Soren)
    pm3 = PostMortemRecord(
        id="PM-BAL-187",
        custom_id="PM-BAL-187",
        recovery_location="Overturned Bogie near Goods Train collision point (Track Km 254)",
        mortuary_facility="AIIMS Bhubaneswar Mortuary Unit #2",
        estimated_gender="Male",
        estimated_age_range="40-48",
        estimated_height_cm=166.0,
        hair_observation="Black hair with prominent graying at temporal regions",
        scars_and_birthmarks="Hyper-pigmented birthmark (3x2cm) in right retroauricular area behind ear",
        tattoos_piercings="Religious emblem tattoo (Trishul) visible on right anterior forearm",
        clothing_recovered="Torn dark green cotton textile, denim fragments",
        jewelry_belongings="Heavy stainless steel circular bangle (kada) on right wrist",
        dental_observations="Absence of teeth #8, #9 with signs of long-standing dental prosthesis",
        pathology_notes="Severe crush injury, secondary to carriage compression",
        image_paths=[p3_pm],
        created_at="2023-06-04T07:15:00",
        status="Unidentified"
    )

    # Save to database
    for am in [am1, am2, am3]:
        db.save_am(am)
    for pm in [pm1, pm2, pm3]:
        db.save_pm(pm)

    print("Balasore dataset seeded successfully with 3 AM and 3 PM records.")
