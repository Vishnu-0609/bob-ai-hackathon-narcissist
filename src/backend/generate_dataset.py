import json
import os
import random

# Ensure output directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

random.seed(42)

first_names_m = ["Aarav", "Rohan", "Vikram", "Sunil", "Amit", "Deepak", "Rajesh", "Manoj", "Pradeep", "Sanjay", "Anil", "Rahul", "Dinesh", "Kunal", "Mahesh", "Suresh", "Gopal", "Prakash", "Arun", "Ashok"]
first_names_f = ["Priya", "Ananya", "Sunita", "Pooja", "Rekha", "Anita", "Geeta", "Kavita", "Suman", "Sneha", "Kalyani", "Deepa", "Shanti", "Lata", "Usha", "Rani", "Mamata", "Sarita", "Rupa", "Neeta"]
last_names = ["Patra", "Mohanty", "Pradhan", "Das", "Nayak", "Behera", "Sahoo", "Swain", "Rout", "Panda", "Mishra", "Sethy", "Jena", "Barik", "Samal", "Mahapatra", "Tripathy", "Biswal", "Mallick", "Parida"]

blood_groups = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
scars_list = [
    [{"location": "left forearm", "description": "3 cm healed linear surgical scar"}],
    [{"location": "right knee", "description": "old childhood trauma scar"}],
    [{"location": "forehead", "description": "small stitch mark above right eyebrow"}],
    [{"location": "abdomen", "description": "appendectomy scar"}],
    [{"location": "left shoulder", "description": "burn mark"}],
    [],
]
tattoos_list = [
    [{"location": "right wrist", "description": "Om symbol"}],
    [{"location": "right shoulder", "description": "bird in flight"}],
    [{"location": "left forearm", "description": "name initials"}],
    [{"location": "neck", "description": "small star tattoo"}],
    [],
]
clothing_list = [
    ["blue shirt", "black trousers"],
    ["red kurta", "white pajama"],
    ["green t-shirt", "blue jeans"],
    ["yellow saree", "gold border"],
    ["grey jacket", "dark jeans"],
    ["striped polo shirt", "brown pants"],
    ["white cotton shirt", "navy trousers"],
    ["black t-shirt", "cargo shorts"],
]
jewellery_list = [
    ["silver ring on right index finger"],
    ["gold chain with pendant"],
    ["copper religious kada on right wrist"],
    ["black thread on left ankle"],
    ["titan watch with leather strap"],
    [],
]
sectors = [
    "Coromandel Express Coach B-1", "Coromandel Express Coach B-2", "Coromandel Express Coach B-3",
    "Coromandel Express Coach B-4", "Coromandel Express Coach A-1", "General Unreserved Coach GS-1",
    "General Unreserved Coach GS-2", "Bahanaga Track Near Engine", "Rear Guard Van", "Goods Train Wagon Collision Zone"
]

am_records = []
pm_records = []
ground_truth_pairs = []

# 1. Anchor Key Cases (PM-017 <-> AM-042: Flagship 92-score match)
# AM-042
am_records.append({
    "case_number": "AM-042",
    "name": "Arjun Mohanty",
    "age": 34,
    "sex": "MALE",
    "height_cm": 173.0,
    "weight_kg": 68.0,
    "blood_group": "O+",
    "physical_description": "Medium build, short dark hair, reported traveling in Coach B-3.",
    "scars": [{"location": "left forearm", "description": "3 cm healed linear scar"}],
    "birthmarks": [{"location": "left cheek", "description": "small dark mole"}],
    "tattoos": [{"location": "right shoulder", "description": "bird in flight"}],
    "clothing": ["blue shirt", "dark blue jeans"],
    "jewellery": ["silver ring on right ring finger"],
    "dental_notes": "Mild crowding in lower anterior teeth, dental chart available upon request",
    "medical_history": "Healed left forearm fracture from 2018",
    "implants": [],
    "last_seen_location": "Coromandel Express Coach B-3",
    "last_seen_time": "2023-06-02 18:45",
    "source": "Brother (Devendra Mohanty)",
})

# AM-081 (Competitor candidate, score ~84)
am_records.append({
    "case_number": "AM-081",
    "name": "Alok Nayak",
    "age": 33,
    "sex": "MALE",
    "height_cm": 171.0,
    "weight_kg": 70.0,
    "blood_group": "O+",
    "physical_description": "Medium athletic stature, dark hair.",
    "scars": [{"location": "left forearm", "description": "faint scar"}],
    "birthmarks": [],
    "tattoos": [],
    "clothing": ["blue shirt", "black trousers"],
    "jewellery": ["metal watch"],
    "dental_notes": None,
    "medical_history": None,
    "implants": [],
    "last_seen_location": "Coromandel Express Coach B-3",
    "last_seen_time": "2023-06-02 18:30",
    "source": "Father (K. C. Nayak)",
})

# AM-013 (Third candidate, score ~78)
am_records.append({
    "case_number": "AM-013",
    "name": "Anil Pradhan",
    "age": 36,
    "sex": "MALE",
    "height_cm": 170.0,
    "weight_kg": 65.0,
    "blood_group": "O+",
    "physical_description": "Lean build, mustache.",
    "scars": [],
    "birthmarks": [{"location": "left cheek", "description": "mole"}],
    "tattoos": [{"location": "right shoulder", "description": "tribal tattoo"}],
    "clothing": ["blue shirt"],
    "jewellery": ["silver ring"],
    "dental_notes": None,
    "medical_history": None,
    "implants": [],
    "last_seen_location": "Coromandel Express Coach B-2",
    "last_seen_time": "2023-06-02 18:50",
    "source": "Wife (S. Pradhan)",
})

# PM-017 (Flagship PM Case)
pm_records.append({
    "body_number": "PM-017",
    "estimated_age_min": 32,
    "estimated_age_max": 36,
    "sex": "MALE",
    "height_cm": 172.0,
    "weight_kg": 67.0,
    "blood_group": "O+",
    "physical_description": "Male body, medium build, intact friction ridges on digits.",
    "scars": [{"location": "left forearm", "description": "healed linear surgical scar approx 3 cm"}],
    "birthmarks": [{"location": "left cheek", "description": "small dark mole"}],
    "tattoos": [{"location": "right shoulder", "description": "bird tattoo"}],
    "clothing": ["blue shirt", "dark jeans"],
    "jewellery": ["silver ring on right hand"],
    "dental_findings": None,
    "medical_findings": "Evidence of healed radius/ulna consolidation",
    "implants": [],
    "fingerprint_status": "AVAILABLE",
    "dna_status": "PENDING",
    "recovery_location": "Coromandel Express Coach B-3",
    "examiner": "Dr. Aris Thorne",
})

ground_truth_pairs.append({"pm": "PM-017", "expected_am": "AM-042", "type": "exact_match", "note": "Flagship demo scenario match"})

# Generate 99 more paired & synthetic cases
for i in range(1, 100):
    am_id = f"AM-{i:03d}"
    pm_id = f"PM-{i:03d}"

    # Skip if case numbers clash with anchor cases
    if am_id in ["AM-042", "AM-081", "AM-013"]:
        am_id = f"AM-{i+200:03d}"
    if pm_id == "PM-017":
        pm_id = f"PM-{i+200:03d}"

    is_male = random.random() < 0.7
    sex = "MALE" if is_male else "FEMALE"
    f_names = first_names_m if is_male else first_names_f
    name = f"{random.choice(f_names)} {random.choice(last_names)}"
    age = random.randint(18, 68)
    height = round(random.uniform(155.0, 182.0), 1) if is_male else round(random.uniform(145.0, 168.0), 1)
    weight = round(height - 100 + random.uniform(-10, 15), 1)
    bg = random.choice(blood_groups)
    sector = random.choice(sectors)

    scars = random.choice(scars_list)
    tattoos = random.choice(tattoos_list)
    clothing = random.choice(clothing_list)
    jewellery = random.choice(jewellery_list)

    # Determine case archetype:
    # 0..60: Exact/Close Match
    # 61..75: Partial Match
    # 76..88: Contradiction Case (Sex or Stature or Blood Mismatch)
    # 89..99: Missing Data Case (Incomplete family report)
    archetype = "exact_match"
    if i > 88:
        archetype = "missing_data"
    elif i > 75:
        archetype = "contradiction"
    elif i > 60:
        archetype = "partial_match"

    # Build AM
    am_case = {
        "case_number": am_id,
        "name": name,
        "age": age,
        "sex": sex,
        "height_cm": height,
        "weight_kg": weight,
        "blood_group": bg if archetype != "missing_data" else None,
        "physical_description": f"Reported missing person, {sex.lower()}, age {age}.",
        "scars": scars if archetype != "missing_data" else [],
        "birthmarks": [],
        "tattoos": tattoos,
        "clothing": clothing,
        "jewellery": jewellery,
        "dental_notes": "Upper central incisor mild rotation" if random.random() < 0.3 else None,
        "medical_history": "Previous wrist fracture" if random.random() < 0.2 else None,
        "implants": [],
        "last_seen_location": sector,
        "last_seen_time": "2023-06-02 18:00",
        "source": "Family Missing Report",
    }
    am_records.append(am_case)

    # Build PM counterpart
    if archetype == "exact_match":
        pm_case = {
            "body_number": pm_id,
            "estimated_age_min": max(15, age - 3),
            "estimated_age_max": age + 3,
            "sex": sex,
            "height_cm": round(height + random.uniform(-1.5, 1.5), 1),
            "weight_kg": weight,
            "blood_group": bg,
            "physical_description": f"Unidentified deceased {sex.lower()} recovered from {sector}.",
            "scars": scars,
            "birthmarks": [],
            "tattoos": tattoos,
            "clothing": clothing,
            "jewellery": jewellery,
            "dental_findings": am_case["dental_notes"],
            "medical_findings": am_case["medical_history"],
            "implants": [],
            "fingerprint_status": "AVAILABLE" if random.random() < 0.5 else "NOT_AVAILABLE",
            "dna_status": "PENDING",
            "recovery_location": sector,
            "examiner": "Dr. A. Thorne",
        }
        ground_truth_pairs.append({"pm": pm_id, "expected_am": am_id, "type": "exact_match"})

    elif archetype == "partial_match":
        pm_case = {
            "body_number": pm_id,
            "estimated_age_min": max(15, age - 4),
            "estimated_age_max": age + 4,
            "sex": sex,
            "height_cm": round(height + random.uniform(-4.0, 4.0), 1),
            "weight_kg": weight,
            "blood_group": bg,
            "physical_description": f"Recovered from {sector}.",
            "scars": scars,
            "birthmarks": [],
            "tattoos": [],  # PM missing tattoo
            "clothing": clothing[:1],  # partial clothing
            "jewellery": [],
            "dental_findings": None,
            "medical_findings": None,
            "implants": [],
            "fingerprint_status": "PENDING",
            "dna_status": "PENDING",
            "recovery_location": sector,
            "examiner": "Dr. R. Mishra",
        }
        ground_truth_pairs.append({"pm": pm_id, "expected_am": am_id, "type": "partial_match"})

    elif archetype == "contradiction":
        # Force a contradiction (Sex or Blood group or Extreme height difference)
        contradict_type = random.choice(["sex", "blood_group", "height"])
        c_sex = "FEMALE" if (sex == "MALE" and contradict_type == "sex") else ("MALE" if contradict_type == "sex" else sex)
        c_bg = "AB-" if (bg != "AB-" and contradict_type == "blood_group") else ("O+" if contradict_type == "blood_group" else bg)
        c_height = height + 18.0 if contradict_type == "height" else height

        pm_case = {
            "body_number": pm_id,
            "estimated_age_min": max(15, age - 5),
            "estimated_age_max": age + 5,
            "sex": c_sex,
            "height_cm": round(c_height, 1),
            "weight_kg": weight,
            "blood_group": c_bg,
            "physical_description": f"Recovered from {sector} with anatomical contradictions against report {am_id}.",
            "scars": scars,
            "birthmarks": [],
            "tattoos": [{"location": "left leg", "description": "dragon"}] if tattoos else [],
            "clothing": clothing,
            "jewellery": jewellery,
            "dental_findings": None,
            "medical_findings": None,
            "implants": [],
            "fingerprint_status": "AVAILABLE",
            "dna_status": "PENDING",
            "recovery_location": sector,
            "examiner": "Dr. K. Patnaik",
        }
        ground_truth_pairs.append({"pm": pm_id, "expected_am": am_id, "type": "contradiction", "contradiction_field": contradict_type})

    else:  # missing_data
        pm_case = {
            "body_number": pm_id,
            "estimated_age_min": None,
            "estimated_age_max": None,
            "sex": sex,
            "height_cm": height,
            "weight_kg": None,
            "blood_group": None,
            "physical_description": f"Partial remains / heavily fragmented recovery from {sector}.",
            "scars": [],
            "birthmarks": [],
            "tattoos": tattoos,
            "clothing": clothing,
            "jewellery": [],
            "dental_findings": None,
            "medical_findings": None,
            "implants": [],
            "fingerprint_status": "NOT_AVAILABLE",
            "dna_status": "AVAILABLE",
            "recovery_location": sector,
            "examiner": "Dr. A. Thorne",
        }
        ground_truth_pairs.append({"pm": pm_id, "expected_am": am_id, "type": "missing_data"})

    pm_records.append(pm_case)

# Save JSON datasets
with open(os.path.join(data_dir, "synthetic_am.json"), "w", encoding="utf-8") as f:
    json.dump(am_records, f, indent=2)

with open(os.path.join(data_dir, "synthetic_pm.json"), "w", encoding="utf-8") as f:
    json.dump(pm_records, f, indent=2)

with open(os.path.join(data_dir, "ground_truth.json"), "w", encoding="utf-8") as f:
    json.dump({
        "incident": "INC-2023-BALASORE",
        "description": "Ground truth benchmark mapping for disaster victim candidate identification",
        "total_cases": len(ground_truth_pairs),
        "pairs": ground_truth_pairs,
    }, f, indent=2)

print(f"Generated {len(am_records)} AM records and {len(pm_records)} PM records with {len(ground_truth_pairs)} ground truth pairs.")
