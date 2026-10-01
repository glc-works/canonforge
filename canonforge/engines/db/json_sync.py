"""
Normalized JSON database generation from scanned markdown lore.
"""
import json
from pathlib import Path
from typing import Dict, List, Any

def sync_all_json(
    chars: List[Dict[str, Any]],
    bestiary: List[Dict[str, Any]],
    skills: List[Dict[str, Any]],
    equipment: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    recipes: List[Dict[str, Any]],
    quests: List[Dict[str, Any]],
    factions: List[Dict[str, Any]],
    places: List[Dict[str, Any]]
):
    """Compile all markdown SSOT files into structured data/ JSON files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Characters
    chars_data = []
    for c in chars:
        record = {
            "char_id": c.get("id", ""),
            "char_name": c.get("title", ""),
            "char_type": "hero" if ("status:hero" in c.get("labels", []) or "tag:hero" in c.get("labels", [])) else "npc",
            "faction": c.get("faction", "Neutral"),
            "house": c.get("house", "Unassigned"),
            "generation": c.get("generation", 1),
            "role": c.get("role", "citizen"),
            "status": c.get("entity_status", "Alive"),
            "birthday": c.get("birth_date", ""),
            "birthplace": c.get("birthplace", ""),
            "birth_race": c.get("birth_race", c.get("species", c.get("race", "Human"))),
            "biological_state": c.get("biological_state", "Cyborg (The Forged)" if c.get("forged") else "Pure Flesh"),
            "current_phase": c.get("current_phase", "Phase 1"),
            "level": c.get("level", 1),
            "forged": c.get("forged", False),
            "strength": c.get("strength", 10),
            "dexterity": c.get("dexterity", 10),
            "vitality": c.get("vitality", 10),
            "willpower": c.get("willpower", 10),
            "force": c.get("force", 0),
            "system_affinity": c.get("system_affinity", 0),
            "labels": c.get("labels", []),
            "wiki_path": c.get("_file_path", ""),
            "description_md": c.get("description_md", "")
        }
        cid = c.get("citizen_id")
        record["citizen_ids"] = [{"faction": c.get("faction", "Neutral"), "citizen_id": cid}] if cid else []
        chars_data.append(record)
        
    with open(DATA_DIR / "characters.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/terms/characters/ (OKF v0.3 SSOT)",
            "total": len(chars_data),
            "characters": chars_data
        }, f, indent=2, ensure_ascii=False)
        
    # 2. Bestiary
    bestiary_data = []
    for m in bestiary:
        bestiary_data.append({
            "id": m.get("id", ""),
            "name": m.get("title", ""),
            "classification": m.get("classification", "mob"),
            "origin": m.get("origin", "hearthspawn"),
            "rarity": m.get("rarity", "common"),
            "element": m.get("element", "Dark"),
            "aspect": m.get("aspect", "Attack"),
            "base_hp": m.get("base_hp", 50),
            "base_atk": m.get("base_atk", 10),
            "primary_habitat": m.get("primary_habitat", "The Maw"),
            "danger_rating": m.get("danger_rating", 1),
            "weaknesses": m.get("weaknesses", []),
            "immunities": m.get("immunities", []),
            "signature_drops": m.get("signature_drops", []),
            "labels": m.get("labels", []),
            "wiki_path": m.get("_file_path", ""),
            "description_md": m.get("description_md", "")
        })
        
    with open(DATA_DIR / "monsters.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/database/bestiary/ (OKF v0.3 SSOT)",
            "total": len(bestiary_data),
            "monsters": bestiary_data
        }, f, indent=2, ensure_ascii=False)
        
    # 3. Skills
    skills_data = []
    for s in skills:
        skills_data.append({
            "id": s.get("id", ""),
            "name": s.get("title", ""),
            "job_path": s.get("job_path", "Universal"),
            "tier": s.get("skill_tier", "C"),
            "type": s.get("skill_type", "Strike"),
            "resource_pool": s.get("resource_pool", "SP"),
            "resource_cost": s.get("resource_cost", 0),
            "target": s.get("target", "single_enemy"),
            "primary_effect": s.get("primary_effect", "damage"),
            "effect_magnitude": s.get("effect_magnitude", 1.0),
            "resonance_capable": s.get("resonance_capable", False),
            "polarity_affinity": s.get("polarity_affinity", "Neutral"),
            "legal_races": s.get("legal_races", []),
            "labels": s.get("labels", []),
            "wiki_path": s.get("_file_path", ""),
            "description_md": s.get("description_md", "")
        })
        
    with open(DATA_DIR / "skills.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/database/skills/ (OKF v0.3 SSOT)",
            "total": len(skills_data),
            "skills": skills_data
        }, f, indent=2, ensure_ascii=False)
        
    # 4. Equipment
    equip_data = []
    for eq in equipment:
        equip_data.append({
            "id": eq.get("id", ""),
            "name": eq.get("title", ""),
            "equipment_type": eq.get("equipment_type", "Weapon"),
            "slot": eq.get("slot", "Mainhand"),
            "rarity": eq.get("rarity", "Common"),
            "job_class": eq.get("job_class", "Warrior"),
            "terrestrial_element": eq.get("terrestrial_element", "None"),
            "master_polarity": eq.get("master_polarity", "Neutral"),
            "item_power": eq.get("item_power", 100),
            "base_atk": eq.get("base_atk", 0),
            "base_def": eq.get("base_def", 0),
            "granted_skill": eq.get("granted_skill", ""),
            "labels": eq.get("labels", []),
            "wiki_path": eq.get("_file_path", ""),
            "description_md": eq.get("description_md", "")
        })
        
    with open(DATA_DIR / "equipment.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/database/equipment/ (OKF v0.3 SSOT)",
            "total": len(equip_data),
            "equipment": equip_data
        }, f, indent=2, ensure_ascii=False)

    # 5. Items
    items_data = []
    for it in items:
        items_data.append({
            "id": it.get("id", ""),
            "name": it.get("title", ""),
            "item_kind": it.get("item_kind", "material"),
            "rarity": it.get("rarity", "Common"),
            "terrestrial_element": it.get("terrestrial_element", "None"),
            "master_polarity": it.get("master_polarity", "Neutral"),
            "primary_source": it.get("primary_source", ""),
            "unit_value": it.get("unit_value", 0),
            "crafting_use": it.get("crafting_use", []),
            "labels": it.get("labels", []),
            "wiki_path": it.get("_file_path", ""),
            "description_md": it.get("description_md", "")
        })

    with open(DATA_DIR / "items.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/database/items/ (OKF v0.3 SSOT)",
            "total": len(items_data),
            "items": items_data
        }, f, indent=2, ensure_ascii=False)

    # 6. Recipes
    recipes_data = []
    for r in recipes:
        recipes_data.append({
            "id": r.get("id", ""),
            "name": r.get("title", ""),
            "category": r.get("category", "weapon"),
            "required_station": r.get("required_station", "Workbench"),
            "crafting_time_seconds": r.get("crafting_time_seconds", 0),
            "output_item": r.get("output_item", ""),
            "output_quantity": r.get("output_quantity", 1),
            "ingredients": r.get("ingredients", []),
            "labels": r.get("labels", []),
            "wiki_path": r.get("_file_path", ""),
            "description_md": r.get("description_md", "")
        })

    with open(DATA_DIR / "recipes.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/database/recipes/ (OKF v0.3 SSOT)",
            "total": len(recipes_data),
            "recipes": recipes_data
        }, f, indent=2, ensure_ascii=False)

    # 7. Quests
    quests_data = []
    for q in quests:
        quests_data.append({
            "id": q.get("id", ""),
            "title": q.get("title", ""),
            "quest_tier": q.get("quest_tier", "main_story"),
            "recommended_item_power": q.get("recommended_item_power", 100),
            "giver": q.get("giver", ""),
            "location": q.get("location", ""),
            "novel_scene_counterpart": q.get("novel_scene_counterpart", ""),
            "dialogue_script": q.get("dialogue_script", ""),
            "objectives": q.get("objectives", []),
            "rewards": q.get("rewards", {}),
            "labels": q.get("labels", []),
            "wiki_path": q.get("_file_path", ""),
            "description_md": q.get("description_md", "")
        })

    with open(DATA_DIR / "quests.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/database/quests/ (OKF v0.3 SSOT)",
            "total": len(quests_data),
            "quests": quests_data
        }, f, indent=2, ensure_ascii=False)
        
    # 8. Factions
    factions_data = []
    for fc in factions:
        factions_data.append({
            "id": fc.get("id", ""),
            "name": fc.get("title", ""),
            "ideology": fc.get("ideology", ""),
            "seat_of_power": fc.get("seat_of_power", ""),
            "leadership": fc.get("leadership", ""),
            "currency": fc.get("currency", ""),
            "master_polarity": fc.get("master_polarity", "Neutral"),
            "signature_unit": fc.get("signature_unit", ""),
            "labels": fc.get("labels", []),
            "wiki_path": fc.get("_file_path", ""),
            "description_md": fc.get("description_md", "")
        })
        
    with open(DATA_DIR / "factions.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/terms/factions/ (OKF v0.3 SSOT)",
            "total": len(factions_data),
            "factions": factions_data
        }, f, indent=2, ensure_ascii=False)
        
    # 9. Places
    places_data = []
    for pl in places:
        places_data.append({
            "id": pl.get("id", ""),
            "name": pl.get("title", ""),
            "location_kind": pl.get("location_kind", "territory"),
            "danger_level": pl.get("danger_level", 1),
            "governing_faction": pl.get("governing_faction", "Neutral"),
            "master_polarity": pl.get("master_polarity", "Neutral"),
            "terrestrial_element": pl.get("terrestrial_element", "None"),
            "facilities": pl.get("facilities", []),
            "labels": pl.get("labels", []),
            "wiki_path": pl.get("_file_path", ""),
            "description_md": pl.get("description_md", "")
        })
        
    with open(DATA_DIR / "places.json", "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Auto-compiled from wiki/terms/places/ (OKF v0.3 SSOT)",
            "total": len(places_data),
            "places": places_data
        }, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Synchronized all 9 domain JSON datasets to: {DATA_DIR}/")

# ==============================================================================
# COMPILATION: LORE MARKDOWN -> POSTGRESQL SEEDS
# ==============================================================================

