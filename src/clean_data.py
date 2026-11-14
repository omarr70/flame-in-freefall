import os
import json
import glob
import zipfile
import io

def fix_encoding(data):
    """
    Recursively fixes common Windows-1252 character corruption (e.g., '?' instead of apostrophes)
    across strings, lists, and dictionaries.
    """
    if isinstance(data, str):
        return data.replace("\ufffd", "'").replace("?s ", "'s ").replace("?t ", "'t ")
    elif isinstance(data, list):
        return [fix_encoding(item) for item in data]
    elif isinstance(data, dict):
        return {k: fix_encoding(v) for k, v in data.items()}
    return data

def parse_isa_tab_content(content_lines):
    """
    Cleans the content of i_Investigation.txt by removing empty lines,
    duplicate ontology URLs, and malformed author entries.
    """
    raw_data = {}
    for line in content_lines:
        parts = [p.strip().strip('"') for p in line.strip().split('\t') if p.strip()]
        if len(parts) > 1:
            key = parts[0]
            values = parts[1:]
            # Skip non-informative ontology and status fields for RAG
            if any(skip in key for skip in ["Term Accession", "Term Source", "Status", "orcid"]):
                continue
            # Clean malformed author prefixes
            values = [v.replace("undefined undefined, ", "") for v in values]
            raw_data[key] = values[0] if len(values) == 1 else values

    study_id = raw_data.get("Study Identifier", "Unknown")
    if study_id == "Unknown" or not study_id:
        return None

    # Automatically classify the investigation into NASA's fire safety pillars
    text_blob = (str(raw_data.get("Study Title", "")) + " " + str(raw_data.get("Comment[Objective]", ""))).lower()
    pillars = []
    if any(w in text_blob for w in ["flammability", "ignition", "material", "soot", "spread"]):
        pillars.append("Prevention (Flammability & Ignition)")
    if any(w in text_blob for w in ["smoke", "aerosol", "detect", "sensor", "dust"]):
        pillars.append("Detection (Smoke & Aerosol)")
    if any(w in text_blob for w in ["extinguish", "suppress", "dilution", "inert", "co2", "helium"]):
        pillars.append("Suppression (Extinction & Dilution)")
    if not pillars:
        pillars.append("Fundamental Combustion Physics")

    cleaned_record = {
        "study_id": study_id,
        "title": raw_data.get("Study Title", ""),
        "acronym": raw_data.get("Comment[Investigation Acronym]", ""),
        "fire_safety_pillars": pillars,
        "research_area": raw_data.get("Comment[Research Area]", ""),
        "sub_research_area": raw_data.get("Comment[SubResearch Area]", ""),
        "flight_platform": raw_data.get("Comment[Flight Platform]", ""),
        "hardware": raw_data.get("Comment[Experiment Hardware]", ""),
        "managing_center": raw_data.get("Comment[Managing NASA Center]", ""),
        "hypothesis": raw_data.get("Comment[Hypothesis]", ""),
        "objective": raw_data.get("Comment[Objective]", ""),
        "approach": raw_data.get("Comment[Approach]", ""),
        "earth_impacts": raw_data.get("Comment[Research Impacts]", ""),
        "keywords": raw_data.get("Study Design Type", []),
        "doi": raw_data.get("Comment[DOI]", ""),
        "top_publications": raw_data.get("Study Publication Title", [])[:5]
    }
    
    return fix_encoding(cleaned_record)

def process_raw_folder(raw_dir="Data/raw", output_file="Data/processed/clean_nasa_psi.json"):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    all_studies = {}
    
    # 1. Read uncompressed i_Investigation.txt files directly
    for txt_path in glob.glob(os.path.join(raw_dir, "**", "i_Investigation.txt"), recursive=True):
        with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
            record = parse_isa_tab_content(f.readlines())
            if record:
                all_studies[record["study_id"]] = record
                print(f"[OK] Cleaned from TXT: {record['study_id']} - {record['title'][:40]}...")

    # 2. Extract and parse i_Investigation.txt inside ZIP archives automatically
    for zip_path in glob.glob(os.path.join(raw_dir, "**", "*.zip"), recursive=True):
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                for file_name in z.namelist():
                    if file_name.endswith("i_Investigation.txt"):
                        with z.open(file_name) as f:
                            lines = io.TextIOWrapper(f, encoding='utf-8', errors='replace').readlines()
                            record = parse_isa_tab_content(lines)
                            if record:
                                all_studies[record["study_id"]] = record
                                print(f"[OK] Cleaned from ZIP: {record['study_id']} - {record['title'][:40]}...")
        except Exception as e:
            print(f"[ERROR] Failed reading {zip_path}: {e}")

    final_list = list(all_studies.values())
    with open(output_file, 'w', encoding='utf-8') as out:
        json.dump(final_list, out, indent=2, ensure_ascii=False)
    
    print(f"\n[DONE] Successfully extracted and cleaned {len(final_list)} investigations into: {output_file}")

if __name__ == "__main__":
    process_raw_folder()