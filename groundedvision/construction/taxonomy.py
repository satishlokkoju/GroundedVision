# Construction Progress Taxonomy Module
"""
Module for parsing and filtering construction taxonomies.
Supports class-specific filtering for focused VLM inference.
"""

from typing import List, Dict, Any, Optional

# Construction Taxonomy as a structured dictionary
# Format: Class -> Category -> [Stages]
TAXONOMY_DATA = {
    "Wood": {
        "Deck sheet - Wooden": ["Deck sheet - Wooden"],
        "Structural Beam- Wooden": ["Beam Installed"],
    },
    "Concrete": {
        "Footings": ["Footings Installed"],
        "Micropiles": ["Micropiles Installed"],
        "Soldier Piles": ["Soldier Piles Installed"],
        "Structural Columns - Concrete": ["Column Installed"],
        "Structural Slabs": ["Slab Installed"],
        "Grade Slab": ["Slab Installed"],
        "Slab Demolition": ["Slab Demolished"],
        "Anchor Bolts": ["Anchor Bolts Installed"],
        "Structural Beams - Concrete": ["Beams Installed"],
        "Plinth Beam": ["Beams Installed"],
        "Double Tee": ["Double Tee Installed"],
        "Fire Proofing": ["Beams Fire Proofed", "Columns Fire Proofed"],
        "Screenwall": ["Screen wall Installed"],
        "Vapour barrier": ["Vapour barrier Installed"],
        "parapet wall": ["parapet wall Installed"],
        "Cat Walk Decking": ["Deck Installed"],
        "Matt foundation": ["Foundation installed"],
        "Trenching": ["Trench installed"],
        "CMU Walls (Concrete Masonry Unit)": ["CMU Wall Installed"],
        "Masonry": ["Wall Installed"],
        "Structural Wall": ["Walls Installed"],
        "Cast In Place": ["Cast In Place"],
        "Concrete Wall": ["Concrete Wall Installed"],
    },
    "Doors": {
        "Doors": ["Door Frame", "Door Installed", "Hardware", "Frames - Hollow Metal", "Swing Doors - HM", "Access Doors"],
        "Coiling doors": ["Doors Installed"],
        "Windows": ["Windows Installed"],
        "Cabinets": ["Cabinet Installed"],
    },
    "Walls": {
        "Drywall + Framing": ["Top Track", "Bottom Track", "Framing", "Insulation", "Top out", "Drywall Hung", "Tape & Float", "First Coat Paint"],
        "Wooden Partitions": ["Wooden Framing", "Plywood Installed"],
        "Glass Partitions": ["Framing", "Glass Installed"],
        "Dryfall paint": ["Final Paint"],
        "Wall Demolition": ["Demolished Walls"],
        "Light Weight Concrete Wall": ["Wall Installed"],
        "Wall Tiling": ["Wall Tiling installed"],
        "Wall Cladding": ["Wall Cladding installed"],
        "Green glass": ["Green glass installed"],
        "Backing": ["Backing Installed"],
        "Blocking": ["Blocking Installed"],
        "Metal backing(Drywall Blocking-Wood &Metal)": ["Metal backing installed"],
    },
    "Flooring": {
        "Flooring": ["Epoxy Flooring", "Vinyl Flooring", "Carpet flooring", "Concrete Flooring", "Porcelain florring", 
                     "Vinyl Composite Tiling", "Welded sheet Vinyl Flooring", "Epoxy Resign Flooring",
                     "Resilient heterogeneous sheet flooring", "Poly Aspartic flooring", "Rubber Flooring",
                     "Dal tile flooring", "Flooring Installed"],
        "Pavers": ["Pavers Installed"],
    },
    "Structural Steel": {
        "Structural Beams - Steel": ["Beams Installed"],
        "Structural columns - Steel": ["Columns Installed"],
        "Structural Joists": ["Joists Installed"],
        "Structural Ceiling Framing": ["Structural Framing"],
        "Secondary steel Framing": ["Framing Installed"],
        "Catwalk": ["Catwalk Installed"],
        "Deck slab": ["Deck sheet Erected"],
        "Ductile Iron Pile": ["DIPs Installed", "DIPs Capped"],
    },
    "Ceiling": {
        "GWB - Ceiling": ["Ceiling Grid", "Drywall Hung"],
        "ACT - Acoustic Ceiling Panels": ["Ceiling Grid", "Ceiling Panels Installed"],
        "Wooden Ceiling": ["WPC Metal Framing", "Wooden Panels Installed"],
        "Wall Protection": ["Wall Protection applied"],
        "Sofits": ["Framing", "Drywall Hung"],
    },
    "Fire Protection": {
        "Fire Protection": ["Horizontal Piping"],
        "Smoke detectors": ["Smoke detectors"],
        "Sprinklers": ["Sprinklers Installed", "Sprinklers Head Installed"],
        "Fire Alarm": ["Fire Alarm Installed"],
        "Speakers": ["Speakers Installed"],
        "FA Strobe": ["FA Strobe Installed"],
        "FA horn & Strobe": ["FA horn & Strobe Installed"],
    },
    "Plumbing": {
        "Plumbing-Domestic": ["Horizontal Piping"],
        "Underground Storm Sewer": ["Storm Piping Installed", "Manhole Installed", "Trench drain Installed"],
        "Plumbing-Drainage": ["Horizontal Piping"],
        "Fuel Piping": ["Fueling piping Installed"],
        "Plumbing Risers": ["Risers Installed"],
        "PEX Lines": ["PEX pipes Installed"],
    },
    "Electrical": {
        "Electrical Outlets": ["Outlet Box Installed"],
        "Transformer": ["Transformer Installed"],
        "Generator": ["Generator Installed"],
        "Cable Bus Duct": ["Cable Bus Duct Installed"],
        "Switch gear": ["Switch gear Installed"],
        "UPS": ["UPS Installed"],
        "Switches": ["Switches Installed"],
        "Electrical Conduit": ["Conduit Pipe Installed"],
        "Cable Tray": ["Cable Tray Installed"],
        "Sleeves": ["Sleeves Installed"],
        "Electrical Lights": ["Lights Installed"],
        "Light Fixtures": ["Light Fixtures"],
        "Junction Box": ["Junction Box"],
    },
    "Mechanical": {
        "Mechanical Duct": ["Duct Installed", "Duct Insulation"],
        "Mechanical Piping": ["Pipes Installed", "Pipes Insulation"],
        "Mechanical Piping Risers": ["Risers Installed"],
        "Conveyor": ["Conveyor Framing", "Conveyor Belt Installed"],
        "AHU (Air Handling Unit)": ["AHU Installed"],
        "FCU (Fan Coil Unit)": ["FCU Installed"],
        "Dehumidifiers": ["Dehumidifiers Installed"],
        "HVAC (Heating, Ventilation and Air Conditioning)": ["HVAC Installed"],
        "VESDA (Very Early Smoke Detection Apparatus)  Piping": ["VESDA Pipes Installed"],
        "Diffuser": ["Diffuser Installed"],
        "Exhaust Grill": ["Exhaust Grill"],
        "Linear Diffuser": ["Linear Diffuser"],
        "Mechanical Piping-Refrigerator": ["Pipes Installed"],
        "Mechanical Piping-Chiilled water": ["Pipes Installed"],
        "VAV (Variable Air Volume)": ["VAV Installed"],
        "Eye Ball Diffuser": ["Eye Ball Diffuser"],
    },
    "Communication": {
        "Cable Tray-Electrical": ["Cable Tray Installed"],
        "Cable Tray-Telecom": ["Cable Tray Installed"],
        "Wireless Access Point": ["Wireless Access Point"],
        "Occupancy sensor": ["Occupancy sensor Installed"],
        "Access Panel": ["Access Panel Installed"],
        "Motion Detector/Glass Break": ["Motion Detector/Glass Break"],
    },
}

# Class groupings for common use cases
MEP_CLASSES = ["Mechanical", "Electrical", "Plumbing", "Fire Protection"]
STRUCTURAL_CLASSES = ["Concrete", "Structural Steel", "Wood"]
FINISHES_CLASSES = ["Walls", "Ceiling", "Flooring", "Doors"]


def get_all_classes() -> List[str]:
    """Return all available class names."""
    return list(TAXONOMY_DATA.keys())


def get_triplets(classes: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """
    Get taxonomy triplets, optionally filtered by class names.
    
    Args:
        classes: Optional list of class names to include. 
                 If None, returns all triplets.
    
    Returns:
        List of dicts with keys: class_name, category, stage
    """
    triplets = []
    target_classes = classes if classes else get_all_classes()
    
    for class_name in target_classes:
        if class_name not in TAXONOMY_DATA:
            continue
        for category, stages in TAXONOMY_DATA[class_name].items():
            for stage in stages:
                triplets.append({
                    "class_name": class_name,
                    "category": category,
                    "stage": stage
                })
    return triplets


def get_markdown_table(classes: Optional[List[str]] = None) -> str:
    """
    Generate markdown table for taxonomy, optionally filtered by class.
    
    Args:
        classes: Optional list of class names to include.
    
    Returns:
        Markdown table string
    """
    triplets = get_triplets(classes)
    lines = [
        "| Class | Category | Stage |",
        "|:------|:---------|:------|"
    ]
    for t in triplets:
        lines.append(f"| {t['class_name']} | {t['category']} | {t['stage']} |")
    return "\n".join(lines)


def parse_markdown_taxonomy(md_table: str) -> List[Dict[str, str]]:
    """
    Parse a markdown table into triplets.
    Legacy function for backward compatibility.
    """
    valid_triplets = []
    lines = md_table.strip().split('\n')
    start_parsing = False
    
    for line in lines:
        if "Class" in line and "Category" in line:
            start_parsing = True
            continue
        if "---" in line:
            continue
        if not start_parsing:
            continue
            
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        
        if len(cells) >= 3:
            triplet = {
                "class_name": cells[0],
                "category": cells[1],
                "stage": cells[2]
            }
            valid_triplets.append(triplet)
            
    return valid_triplets
