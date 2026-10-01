#!/usr/bin/env python3
"""
CONVERGENCE STUDIO: MASTER SENSORY LEXEME DICTIONARY
------------------------------------------------------------------------------
Authoritative lexicographic data structure and O(1) inverted lookup index
for literary sensory analysis. Handles:
1. Explicit irregular English inflections (froze -> freeze, ground -> grind, etc.)
2. Morphological form expansion (plurals, participles, past tenses, adjectival derivations)
3. Multi-sensory tagging (e.g. 'cider' -> taste + smell; 'scald' -> touch + thermal hot)
4. Atmospheric vectors (Thermal: Warm vs Cold, Tactile: Hard vs Soft)
------------------------------------------------------------------------------
"""

import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
DATA_DIR = PACKAGE_ROOT / "data"
PROFILES_DIR = DATA_DIR / "sensory_profiles"
DICTIONARY_CACHE_FILE = DATA_DIR / "master_sensory_dictionary.json"

class SensoryLexeme:
    def __init__(
        self,
        lemma: str,
        senses: List[str],
        forms: List[str],
        pos: str = "adj",
        thematic_tags: Optional[List[str]] = None,
        thermal: Optional[str] = None,
        tactile: Optional[str] = None,
        intensity: int = 2,
        synonyms: Optional[List[str]] = None,
        antonyms: Optional[List[str]] = None,
        aliases: Optional[List[str]] = None,
        notes: str = ""
    ):
        self.lemma = lemma.lower()
        self.senses = [s.lower() for s in senses]
        self.forms = set(f.lower() for f in forms)
        # Ensure lemma itself is in forms
        self.forms.add(self.lemma)
        self.pos = pos
        self.thematic_tags = set(t.lower() for t in (thematic_tags or ["core"]))
        self.thermal = thermal
        self.tactile = tactile
        self.intensity = int(intensity) if intensity in [1, 2, 3] else 2
        self.synonyms = set(s.lower().strip() for s in (synonyms or []))
        self.antonyms = set(a.lower().strip() for a in (antonyms or []))
        self.aliases = set(al.lower().strip() for al in (aliases or []))
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "lemma": self.lemma,
            "senses": self.senses,
            "pos": self.pos,
            "forms": sorted(list(self.forms)),
            "themes": sorted(list(self.thematic_tags)),
            "thermal": self.thermal,
            "tactile": self.tactile,
            "intensity": self.intensity,
        }
        if self.synonyms:
            d["synonyms"] = sorted(list(self.synonyms))
        if self.antonyms:
            d["antonyms"] = sorted(list(self.antonyms))
        if self.aliases:
            d["aliases"] = sorted(list(self.aliases))
        if self.notes:
            d["description"] = self.notes
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SensoryLexeme":
        return cls(
            lemma=d["lemma"],
            senses=d.get("senses", []),
            forms=d.get("forms", [d["lemma"]]),
            pos=d.get("pos", "adj"),
            thematic_tags=d.get("themes") or d.get("thematic_tags", []),
            thermal=d.get("thermal"),
            tactile=d.get("tactile"),
            intensity=d.get("intensity", 2),
            synonyms=d.get("synonyms", []),
            antonyms=d.get("antonyms", []),
            aliases=d.get("aliases", []),
            notes=d.get("description") or d.get("notes", "")
        )

# ==============================================================================
# CANONICAL SENSORY LEXEME REPOSITORY (RICH ENGLISH LITERARY VOCABULARY)
# ==============================================================================

CANONICAL_LEXEMES: List[SensoryLexeme] = [
    # --------------------------------------------------------------------------
    # TOUCH & THERMAL & KINETIC
    # --------------------------------------------------------------------------
    SensoryLexeme("freeze", ["touch"], ["freeze", "freezes", "freezing", "froze", "frozen", "frost", "frosty", "frostbite"], pos="verb", thermal="cold", tactile="hard", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("chill", ["touch"], ["chill", "chills", "chilled", "chilling", "chilly"], pos="verb", thermal="cold", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("cold", ["touch"], ["cold", "colder", "coldest", "coldly", "coldness"], pos="adj", thermal="cold", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("sleet", ["touch", "sight"], ["sleet", "sleeting", "sleety"], pos="noun", thermal="cold", thematic_tags=["grimdark"]),
    SensoryLexeme("frazil", ["touch", "sight"], ["frazil", "frazils"], pos="noun", thermal="cold", tactile="hard", thematic_tags=["grimdark", "foundry"], notes="Needle-like slush ice"),
    SensoryLexeme("slush", ["touch", "sight"], ["slush", "slushy", "slushing"], pos="noun", thermal="cold", tactile="soft", thematic_tags=["grimdark"]),
    SensoryLexeme("numb", ["touch"], ["numb", "numbs", "numbing", "numbed", "numbness", "numbly"], pos="adj", thermal="cold", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("shiver", ["touch"], ["shiver", "shivers", "shivering", "shivered"], pos="verb", thermal="cold", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("shudder", ["touch", "sound"], ["shudder", "shudders", "shuddering", "shuddered"], pos="verb", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("burn", ["touch"], ["burn", "burns", "burning", "burned", "burnt"], pos="verb", thermal="warm", thematic_tags=["hearth", "foundry", "core"]),
    SensoryLexeme("warm", ["touch"], ["warm", "warms", "warming", "warmed", "warmth", "warmly", "warmer", "warmest"], pos="adj", thermal="warm", tactile="soft", thematic_tags=["hearth", "core"]),
    SensoryLexeme("hot", ["touch"], ["hot", "hotter", "hottest", "hotly", "heat", "heating", "heated"], pos="adj", thermal="warm", thematic_tags=["hearth", "foundry", "core"]),
    SensoryLexeme("scorch", ["touch", "sight", "smell"], ["scorch", "scorches", "scorching", "scorched"], pos="verb", thermal="warm", thematic_tags=["foundry", "hearth"]),
    SensoryLexeme("scald", ["touch"], ["scald", "scalds", "scalding", "scalded"], pos="verb", thermal="warm", thematic_tags=["foundry", "hearth"]),
    SensoryLexeme("sear", ["touch"], ["sear", "sears", "searing", "seared"], pos="verb", thermal="warm", thematic_tags=["foundry", "military"]),
    SensoryLexeme("ember", ["sight", "touch"], ["ember", "embers", "ember-glow"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("hearth", ["sight", "touch"], ["hearth", "hearths", "hearth-fire", "hearth-flame", "hearthside"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("flame", ["sight", "touch"], ["flame", "flames", "flaming", "flamed"], pos="noun", thermal="warm", thematic_tags=["hearth", "foundry", "core"]),
    SensoryLexeme("blister", ["touch"], ["blister", "blisters", "blistering", "blistered"], pos="noun", thermal="warm", thematic_tags=["foundry", "military"]),
    SensoryLexeme("grind", ["sound", "touch"], ["grind", "grinds", "grinding", "ground"], pos="verb", tactile="hard", thematic_tags=["foundry", "military"]),
    SensoryLexeme("strike", ["touch", "sound"], ["strike", "strikes", "striking", "struck", "stricken"], pos="verb", tactile="hard", thematic_tags=["foundry", "military"]),
    SensoryLexeme("bleed", ["sight", "touch"], ["bleed", "bleeds", "bleeding", "bled"], pos="verb", thematic_tags=["military"]),
    SensoryLexeme("bite", ["touch", "taste"], ["bite", "bites", "biting", "bit", "bitten"], pos="verb", thematic_tags=["military", "core"]),
    SensoryLexeme("clutch", ["touch"], ["clutch", "clutches", "clutching", "clutched"], pos="verb", tactile="hard", thematic_tags=["core"]),
    SensoryLexeme("grip", ["touch"], ["grip", "grips", "gripping", "gripped"], pos="verb", tactile="hard", thematic_tags=["core"]),
    SensoryLexeme("grasp", ["touch"], ["grasp", "grasps", "grasping", "grasped"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("seize", ["touch"], ["seize", "seizes", "seizing", "seized"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("cling", ["touch"], ["cling", "clings", "clinging", "clung"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("tear", ["touch"], ["tear", "tears", "tearing", "tore", "torn"], pos="verb", thematic_tags=["military", "core"]),
    SensoryLexeme("crush", ["touch"], ["crush", "crushes", "crushing", "crushed"], pos="verb", tactile="hard", thematic_tags=["foundry", "military"]),
    SensoryLexeme("scrape", ["touch", "sound"], ["scrape", "scrapes", "scraping", "scraped"], pos="verb", tactile="hard", thematic_tags=["foundry", "core"]),
    SensoryLexeme("friction", ["touch"], ["friction", "frictional"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("vibration", ["touch", "sound"], ["vibration", "vibrations", "vibrate", "vibrates", "vibrating", "vibrated"], pos="noun", thematic_tags=["foundry", "fantasy"]),
    SensoryLexeme("heavy", ["touch"], ["heavy", "heavier", "heaviest", "heavily", "heaviness", "heft", "hefty"], pos="adj", tactile="hard", thematic_tags=["core", "foundry"]),
    SensoryLexeme("leaden", ["touch", "sight"], ["leaden", "leadenly", "lead"], pos="adj", thermal="cold", tactile="hard", thematic_tags=["grimdark", "foundry"]),
    SensoryLexeme("iron", ["touch", "sight"], ["iron", "irons", "iron-hard", "iron-clad", "iron-bound"], pos="noun", tactile="hard", thematic_tags=["foundry", "military"]),
    SensoryLexeme("brass", ["touch", "sight"], ["brass", "brassy"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("steel", ["touch", "sight"], ["steel", "steely"], pos="noun", tactile="hard", thematic_tags=["foundry", "military"]),
    SensoryLexeme("bronze", ["touch", "sight"], ["bronze", "bronzed"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("anvil", ["touch", "sight"], ["anvil", "anvils"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("hammer", ["touch", "sound"], ["hammer", "hammers", "hammering", "hammered", "hammer-blow"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("burr", ["touch"], ["burr", "burrs", "burred"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("coarse", ["touch"], ["coarse", "coarser", "coarsest", "coarsely", "coarseness"], pos="adj", tactile="hard", thematic_tags=["core"]),
    SensoryLexeme("gritty", ["touch"], ["gritty", "grit", "grittiness"], pos="adj", tactile="hard", thematic_tags=["foundry", "military"]),
    SensoryLexeme("rough", ["touch"], ["rough", "rougher", "roughest", "roughly", "roughness", "rough-hewn"], pos="adj", tactile="hard", thematic_tags=["core"]),
    SensoryLexeme("smooth", ["touch"], ["smooth", "smoother", "smoothest", "smoothly", "smoothness", "smoothed", "smoothing"], pos="adj", tactile="soft", thematic_tags=["core", "fantasy"]),
    SensoryLexeme("slick", ["touch"], ["slick", "slicker", "slickest", "slickly"], pos="adj", thematic_tags=["core", "foundry"]),
    SensoryLexeme("slimy", ["touch"], ["slimy", "slime", "sliminess"], pos="adj", thematic_tags=["grimdark"]),
    SensoryLexeme("greasy", ["touch", "taste"], ["greasy", "grease", "greased", "greasing", "greasiness"], pos="adj", thematic_tags=["foundry", "hearth"]),
    SensoryLexeme("wool", ["touch"], ["wool", "woolen", "woollens", "wooly"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("linen", ["touch"], ["linen", "linens"], pos="noun", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("silk", ["touch"], ["silk", "silken", "silky"], pos="noun", tactile="soft", thematic_tags=["fantasy", "hearth"]),
    SensoryLexeme("velvet", ["touch"], ["velvet", "velvety"], pos="noun", tactile="soft", thematic_tags=["fantasy"]),
    SensoryLexeme("blanket", ["touch"], ["blanket", "blankets", "blanketed"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("quilt", ["touch"], ["quilt", "quilts", "quilted"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("dough", ["touch", "taste"], ["dough", "doughy"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),

    # --------------------------------------------------------------------------
    # SOUND & ACOUSTICS
    # --------------------------------------------------------------------------
    SensoryLexeme("crackle", ["sound"], ["crackle", "crackles", "crackling", "crackled"], pos="verb", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("sputter", ["sound"], ["sputter", "sputters", "sputtering", "sputtered"], pos="verb", thematic_tags=["hearth", "foundry"]),
    SensoryLexeme("simmer", ["sound"], ["simmer", "simmers", "simmering", "simmered"], pos="verb", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("bubble", ["sound"], ["bubble", "bubbles", "bubbling", "bubbled"], pos="verb", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("hiss", ["sound"], ["hiss", "hisses", "hissing", "hissed"], pos="verb", thematic_tags=["foundry", "hearth", "core"]),
    SensoryLexeme("clank", ["sound"], ["clank", "clanks", "clanking", "clanked"], pos="verb", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("clang", ["sound"], ["clang", "clangs", "clanging", "clanged", "clangor"], pos="verb", tactile="hard", thematic_tags=["foundry", "military"]),
    SensoryLexeme("groan", ["sound"], ["groan", "groans", "groaning", "groaned"], pos="verb", thematic_tags=["core", "foundry", "military"]),
    SensoryLexeme("shriek", ["sound"], ["shriek", "shrieks", "shrieking", "shrieked"], pos="verb", thematic_tags=["military", "foundry"]),
    SensoryLexeme("screech", ["sound"], ["screech", "screeches", "screeching", "screeched"], pos="verb", thematic_tags=["foundry", "military"]),
    SensoryLexeme("rattle", ["sound"], ["rattle", "rattles", "rattling", "rattled"], pos="verb", thematic_tags=["foundry", "military", "core"]),
    SensoryLexeme("creak", ["sound"], ["creak", "creaks", "creaking", "creaked", "creaky"], pos="verb", thematic_tags=["core", "hearth"]),
    SensoryLexeme("hum", ["sound"], ["hum", "hums", "humming", "hummed"], pos="verb", thematic_tags=["foundry", "fantasy", "core"]),
    SensoryLexeme("drone", ["sound"], ["drone", "drones", "droning", "droned"], pos="verb", thematic_tags=["foundry", "fantasy"]),
    SensoryLexeme("chime", ["sound"], ["chime", "chimes", "chiming", "chimed"], pos="verb", thematic_tags=["fantasy", "hearth"]),
    SensoryLexeme("ring", ["sound"], ["ring", "rings", "ringing", "rang", "rung"], pos="verb", thematic_tags=["fantasy", "foundry", "core"]),
    SensoryLexeme("sing", ["sound"], ["sing", "sings", "singing", "sang", "sung", "song"], pos="verb", thematic_tags=["fantasy"]),
    SensoryLexeme("thud", ["sound"], ["thud", "thuds", "thudding", "thudded"], pos="noun", tactile="hard", thematic_tags=["core", "foundry"]),
    SensoryLexeme("thump", ["sound"], ["thump", "thumps", "thumping", "thumped"], pos="noun", thematic_tags=["core", "foundry"]),
    SensoryLexeme("whisper", ["sound"], ["whisper", "whispers", "whispering", "whispered"], pos="verb", thematic_tags=["core", "fantasy"]),
    SensoryLexeme("rustle", ["sound"], ["rustle", "rustles", "rustling", "rustled"], pos="verb", thematic_tags=["hearth", "core"]),
    SensoryLexeme("sizzle", ["sound"], ["sizzle", "sizzles", "sizzling", "sizzled"], pos="verb", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("clink", ["sound"], ["clink", "clinks", "clinking", "clinked"], pos="verb", thematic_tags=["hearth", "core"]),
    SensoryLexeme("clatter", ["sound"], ["clatter", "clatters", "clattering", "clattered"], pos="verb", thematic_tags=["hearth", "foundry"]),
    SensoryLexeme("whistle", ["sound"], ["whistle", "whistles", "whistling", "whistled"], pos="verb", thematic_tags=["foundry", "hearth", "core"]),
    SensoryLexeme("echo", ["sound"], ["echo", "echoes", "echoing", "echoed"], pos="verb", thematic_tags=["core", "fantasy"]),
    SensoryLexeme("resonance", ["sound"], ["resonance", "resonant", "resonate", "resonates", "resonating", "resonated"], pos="noun", thematic_tags=["fantasy", "foundry"]),
    SensoryLexeme("gasp", ["sound"], ["gasp", "gasps", "gasping", "gasped"], pos="verb", thematic_tags=["core", "military"]),
    SensoryLexeme("sob", ["sound"], ["sob", "sobs", "sobbing", "sobbed"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("snore", ["sound"], ["snore", "snores", "snoring", "snored"], pos="verb", thematic_tags=["hearth"]),
    SensoryLexeme("howl", ["sound"], ["howl", "howls", "howling", "howled"], pos="verb", thematic_tags=["military", "core"]),
    SensoryLexeme("bellow", ["sound"], ["bellow", "bellows", "bellowing", "bellowed"], pos="verb", thematic_tags=["military", "foundry"]),
    SensoryLexeme("snarl", ["sound"], ["snarl", "snarls", "snarling", "snarled"], pos="verb", thematic_tags=["military", "core"]),
    SensoryLexeme("wheeze", ["sound"], ["wheeze", "wheezes", "wheezing", "wheezed"], pos="verb", thematic_tags=["military", "core"]),
    SensoryLexeme("rasp", ["sound"], ["rasp", "rasps", "rasping", "rasped", "raspy"], pos="verb", thematic_tags=["military", "foundry"]),
    SensoryLexeme("squelch", ["sound"], ["squelch", "squelches", "squelching", "squelched"], pos="verb", thematic_tags=["grimdark"]),

    # --------------------------------------------------------------------------
    # SMELL & OLFACTORY
    # --------------------------------------------------------------------------
    SensoryLexeme("smell", ["smell"], ["smell", "smells", "smelling", "smelled", "smelt"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("scent", ["smell"], ["scent", "scents", "scented", "scenting"], pos="noun", thematic_tags=["core", "fantasy"]),
    SensoryLexeme("odor", ["smell"], ["odor", "odors", "odorous"], pos="noun", thematic_tags=["core"]),
    SensoryLexeme("smoke", ["smell", "sight"], ["smoke", "smokes", "smoking", "smoked", "smoky", "woodsmoke"], pos="noun", thermal="warm", thematic_tags=["hearth", "foundry", "core"]),
    SensoryLexeme("sulfur", ["smell"], ["sulfur", "sulphur", "sulfurous", "sulphurous"], pos="noun", thermal="warm", thematic_tags=["foundry"]),
    SensoryLexeme("tallow", ["smell", "touch"], ["tallow", "tallowy"], pos="noun", thermal="warm", thematic_tags=["hearth", "foundry", "military"]),
    SensoryLexeme("cedar", ["smell", "touch"], ["cedar", "cedarwood"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("pine", ["smell"], ["pine", "pines", "pine-pitch", "pine-needles"], pos="noun", thermal="cold", thematic_tags=["hearth", "core"]),
    SensoryLexeme("peat", ["smell"], ["peat", "peaty", "peat-smoke"], pos="noun", thematic_tags=["hearth", "grimdark"]),
    SensoryLexeme("ozone", ["smell"], ["ozone"], pos="noun", thematic_tags=["fantasy", "foundry"]),
    SensoryLexeme("incense", ["smell"], ["incense", "incenses"], pos="noun", thematic_tags=["fantasy"]),
    SensoryLexeme("yeast", ["smell", "taste"], ["yeast", "yeasty"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("bread", ["smell", "taste"], ["bread", "breads"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("bacon", ["smell", "taste"], ["bacon"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("parsnip", ["smell", "taste"], ["parsnip", "parsnips"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("persimmon", ["smell", "taste"], ["persimmon", "persimmons"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("chicory", ["smell", "taste"], ["chicory"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("roast", ["smell", "taste"], ["roast", "roasts", "roasting", "roasted"], pos="verb", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("cider", ["smell", "taste"], ["cider", "ciders"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("stew", ["smell", "taste"], ["stew", "stews", "stewing", "stewed"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("thyme", ["smell", "taste"], ["thyme"], pos="noun", thematic_tags=["hearth"]),
    SensoryLexeme("rosemary", ["smell", "taste"], ["rosemary"], pos="noun", thematic_tags=["hearth"]),
    SensoryLexeme("chamomile", ["smell", "taste"], ["chamomile"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("mint", ["smell", "taste"], ["mint", "minty", "peppermint"], pos="noun", thermal="cold", thematic_tags=["hearth", "fantasy"]),
    SensoryLexeme("cinnamon", ["smell", "taste"], ["cinnamon"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("clove", ["smell", "taste"], ["clove", "cloves"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("beeswax", ["smell", "touch"], ["beeswax", "wax", "waxy"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth", "fantasy"]),
    SensoryLexeme("blood", ["smell", "taste", "sight"], ["blood", "bloody", "bloodied", "bloodshed"], pos="noun", thermal="warm", thematic_tags=["military", "grimdark"]),
    SensoryLexeme("rot", ["smell"], ["rot", "rots", "rotting", "rotted", "rotten"], pos="verb", thematic_tags=["grimdark"]),
    SensoryLexeme("stench", ["smell"], ["stench", "stenches"], pos="noun", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("reek", ["smell"], ["reek", "reeks", "reeking", "reeked"], pos="verb", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("ammonia", ["smell"], ["ammonia"], pos="noun", thematic_tags=["grimdark", "foundry"]),
    SensoryLexeme("bile", ["smell", "taste"], ["bile"], pos="noun", thematic_tags=["grimdark"]),
    SensoryLexeme("vinegar", ["smell", "taste"], ["vinegar"], pos="noun", thematic_tags=["grimdark", "hearth"]),
    SensoryLexeme("gangrene", ["smell", "sight"], ["gangrene", "gangrenous"], pos="noun", thematic_tags=["grimdark"]),
    SensoryLexeme("rancid", ["smell", "taste"], ["rancid", "rancidity"], pos="adj", thematic_tags=["grimdark", "foundry"]),
    SensoryLexeme("carrion", ["smell", "sight"], ["carrion"], pos="noun", thematic_tags=["grimdark"]),
    SensoryLexeme("acrid", ["smell", "taste"], ["acrid", "acridly", "acridity"], pos="adj", thematic_tags=["foundry", "core"]),
    SensoryLexeme("pungent", ["smell", "taste"], ["pungent", "pungently", "pungency"], pos="adj", thematic_tags=["core"]),
    SensoryLexeme("fragrant", ["smell"], ["fragrant", "fragrantly", "fragrance", "fragrances"], pos="adj", thematic_tags=["core", "fantasy"]),
    SensoryLexeme("petrichor", ["smell"], ["petrichor"], pos="noun", thematic_tags=["core"]),

    # --------------------------------------------------------------------------
    # TASTE & GUSTATORY
    # --------------------------------------------------------------------------
    SensoryLexeme("taste", ["taste"], ["taste", "tastes", "tasting", "tasted", "tasty"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("bitter", ["taste"], ["bitter", "bitterly", "bitterness"], pos="adj", thematic_tags=["core", "grimdark"]),
    SensoryLexeme("sour", ["taste"], ["sour", "sourly", "sourness"], pos="adj", thematic_tags=["core", "grimdark"]),
    SensoryLexeme("sweet", ["taste"], ["sweet", "sweeter", "sweetest", "sweetly", "sweetness"], pos="adj", thermal="warm", thematic_tags=["core", "hearth"]),
    SensoryLexeme("salt", ["taste"], ["salt", "salts", "salty", "saltier", "saltiest", "salted", "salting", "brine", "briny"], pos="noun", thematic_tags=["core", "hearth", "military"]),
    SensoryLexeme("savory", ["taste"], ["savory", "savoury", "savoriness"], pos="adj", thermal="warm", thematic_tags=["hearth", "core"]),
    SensoryLexeme("tart", ["taste"], ["tart", "tartly", "tartness"], pos="adj", thematic_tags=["hearth", "core"]),
    SensoryLexeme("tang", ["taste"], ["tang", "tangy"], pos="noun", thematic_tags=["core"]),
    SensoryLexeme("astringent", ["taste"], ["astringent", "astringently"], pos="adj", thematic_tags=["core", "grimdark"]),
    SensoryLexeme("rye", ["taste"], ["rye"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("leek", ["taste", "smell"], ["leek", "leeks"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("porridge", ["taste"], ["porridge"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth"]),
    SensoryLexeme("crust", ["taste", "touch"], ["crust", "crusts", "crusted", "crusty"], pos="noun", tactile="hard", thematic_tags=["hearth"]),
    SensoryLexeme("biscuit", ["taste"], ["biscuit", "biscuits"], pos="noun", thematic_tags=["hearth"]),
    SensoryLexeme("tea", ["taste", "smell"], ["tea", "teas"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("honey", ["taste", "smell"], ["honey", "honeyed"], pos="noun", thermal="warm", tactile="soft", thematic_tags=["hearth", "fantasy"]),
    SensoryLexeme("mutton", ["taste"], ["mutton"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("ginger", ["taste", "smell"], ["ginger", "gingery"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("sourdough", ["taste", "smell"], ["sourdough"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("ale", ["taste"], ["ale", "ales"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("marrow", ["taste"], ["marrow"], pos="noun", thermal="warm", thematic_tags=["hearth"]),
    SensoryLexeme("copper", ["taste", "touch"], ["copper", "coppery"], pos="noun", tactile="hard", thematic_tags=["military", "foundry"]),
    SensoryLexeme("hardtack", ["taste"], ["hardtack"], pos="noun", tactile="hard", thematic_tags=["military"]),
    SensoryLexeme("parched", ["taste"], ["parched", "parch"], pos="adj", thermal="warm", thematic_tags=["military", "core"]),
    SensoryLexeme("chew", ["taste"], ["chew", "chews", "chewing", "chewed"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("swallow", ["taste"], ["swallow", "swallows", "swallowing", "swallowed"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("sip", ["taste"], ["sip", "sips", "sipping", "sipped"], pos="verb", thematic_tags=["hearth", "core"]),
    SensoryLexeme("gulp", ["taste"], ["gulp", "gulps", "gulping", "gulped"], pos="verb", thematic_tags=["core"]),

    # --------------------------------------------------------------------------
    # SIGHT & VISUALS
    # --------------------------------------------------------------------------
    SensoryLexeme("shadow", ["sight"], ["shadow", "shadows", "shadowy"], pos="noun", thematic_tags=["core"]),
    SensoryLexeme("silhouette", ["sight"], ["silhouette", "silhouettes", "silhouetted"], pos="noun", thematic_tags=["core"]),
    SensoryLexeme("glint", ["sight"], ["glint", "glints", "glinting", "glinted"], pos="verb", thematic_tags=["core", "foundry"]),
    SensoryLexeme("gleam", ["sight"], ["gleam", "gleams", "gleaming", "gleamed"], pos="verb", thematic_tags=["core", "hearth", "fantasy"]),
    SensoryLexeme("glow", ["sight"], ["glow", "glows", "glowing", "glowed"], pos="verb", thermal="warm", thematic_tags=["core", "hearth", "fantasy"]),
    SensoryLexeme("flicker", ["sight"], ["flicker", "flickers", "flickering", "flickered"], pos="verb", thematic_tags=["core", "hearth"]),
    SensoryLexeme("shimmer", ["sight"], ["shimmer", "shimmers", "shimmering", "shimmered"], pos="verb", thematic_tags=["core", "fantasy"]),
    SensoryLexeme("shine", ["sight"], ["shine", "shines", "shining", "shone", "shined"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("spark", ["sight"], ["spark", "sparks", "sparking", "sparked"], pos="noun", thermal="warm", thematic_tags=["foundry", "hearth", "core"]),
    SensoryLexeme("pale", ["sight"], ["pale", "paler", "palest", "palely", "paleness", "pallor", "pallid"], pos="adj", thermal="cold", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("amber", ["sight"], ["amber"], pos="noun", thermal="warm", thematic_tags=["hearth", "fantasy"]),
    SensoryLexeme("violet", ["sight"], ["violet"], pos="noun", thematic_tags=["fantasy"]),
    SensoryLexeme("crimson", ["sight"], ["crimson"], pos="adj", thermal="warm", thematic_tags=["military", "grimdark"]),
    SensoryLexeme("scarlet", ["sight"], ["scarlet"], pos="adj", thermal="warm", thematic_tags=["military"]),
    SensoryLexeme("gloom", ["sight"], ["gloom", "gloomy", "gloomily"], pos="noun", thermal="cold", thematic_tags=["grimdark", "core"]),
    SensoryLexeme("dim", ["sight"], ["dim", "dimmer", "dimmest", "dimly", "dimness", "dimmed", "dimming"], pos="adj", thematic_tags=["core"]),
    SensoryLexeme("darkness", ["sight"], ["darkness", "dark", "darker", "darkest", "darkly"], pos="noun", thematic_tags=["core"]),
    SensoryLexeme("quartz", ["sight", "touch"], ["quartz"], pos="noun", tactile="hard", thematic_tags=["fantasy"]),
    SensoryLexeme("crystal", ["sight", "touch"], ["crystal", "crystals", "crystalline"], pos="noun", tactile="hard", thematic_tags=["fantasy"]),
    SensoryLexeme("aether", ["sight", "fantasy"], ["aether", "aetheric"], pos="noun", thematic_tags=["fantasy"]),
    SensoryLexeme("prismatic", ["sight"], ["prismatic", "prism", "prisms"], pos="adj", thematic_tags=["fantasy"]),
    SensoryLexeme("luminescence", ["sight"], ["luminescence", "luminous", "luminously"], pos="noun", thematic_tags=["fantasy"]),
    SensoryLexeme("soot", ["sight", "touch"], ["soot", "sooty"], pos="noun", thermal="warm", thematic_tags=["foundry", "hearth"]),
    SensoryLexeme("slag", ["sight", "touch"], ["slag"], pos="noun", thermal="warm", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("coke", ["sight", "smell"], ["coke"], pos="noun", thermal="warm", thematic_tags=["foundry"]),
    SensoryLexeme("cinder", ["sight", "touch"], ["cinder", "cinders"], pos="noun", thermal="warm", thematic_tags=["foundry", "hearth"]),
    SensoryLexeme("piston", ["sight", "sound"], ["piston", "pistons"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("gear", ["sight", "touch"], ["gear", "gears"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("cog", ["sight", "touch"], ["cog", "cogs"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("boiler", ["sight", "touch"], ["boiler", "boilers"], pos="noun", thermal="warm", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("caliper", ["sight", "touch"], ["caliper", "calipers"], pos="noun", tactile="hard", thematic_tags=["foundry"]),
    SensoryLexeme("steam", ["sight", "touch"], ["steam", "steams", "steaming", "steamed", "steamy"], pos="noun", thermal="warm", thematic_tags=["foundry", "hearth"]),
    SensoryLexeme("stare", ["sight"], ["stare", "stares", "staring", "stared"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("gaze", ["sight"], ["gaze", "gazes", "gazing", "gazed"], pos="verb", thematic_tags=["core"]),
    SensoryLexeme("glance", ["sight"], ["glance", "glances", "glancing", "glanced"], pos="verb", thematic_tags=["core"]),
]

DICTIONARY_YAML_FILE = DATA_DIR / "sensory_dictionary.yaml"

class MasterSensoryDictionary:
    def __init__(self):
        self.metadata: Dict[str, Any] = {}
        self.themes_registry: Dict[str, str] = {}
        self.lexemes: Dict[str, SensoryLexeme] = {}
        # Inverted index: single word -> SensoryLexeme
        self.inverted_index: Dict[str, SensoryLexeme] = {}
        # Phrase index: normalized multi-word phrase ("wood smoke", "blast furnace") -> SensoryLexeme
        self.phrase_index: Dict[str, SensoryLexeme] = {}
        self.max_phrase_len: int = 1
        self.build_index()

    def add_lexeme(self, lexeme: SensoryLexeme):
        self.lexemes[lexeme.lemma] = lexeme
        # 1. Index surface forms
        for form in lexeme.forms:
            form_clean = form.lower().strip()
            words = [w for w in re.split(r"[\s\-]+", form_clean) if w]
            if len(words) == 1:
                self.inverted_index[words[0]] = lexeme
            elif len(words) > 1:
                phrase_key = " ".join(words)
                self.phrase_index[phrase_key] = lexeme
                if len(words) > self.max_phrase_len:
                    self.max_phrase_len = len(words)

        # 2. Index lore aliases
        for alias in lexeme.aliases:
            alias_clean = alias.lower().strip()
            words = [w for w in re.split(r"[\s\-]+", alias_clean) if w]
            if len(words) == 1:
                self.inverted_index[words[0]] = lexeme
            elif len(words) > 1:
                phrase_key = " ".join(words)
                self.phrase_index[phrase_key] = lexeme
                if len(words) > self.max_phrase_len:
                    self.max_phrase_len = len(words)

    def build_index(self):
        self.lexemes.clear()
        self.inverted_index.clear()
        self.phrase_index.clear()
        self.max_phrase_len = 1

        # 1. Load from primary YAML SSOT
        if DICTIONARY_YAML_FILE.is_file():
            try:
                import yaml
                data = yaml.safe_load(DICTIONARY_YAML_FILE.read_text(encoding="utf-8")) or {}
                self.themes_registry = data.get("themes_registry", {})
                for item in data.get("lexemes", []):
                    lex = SensoryLexeme.from_dict(item)
                    self.add_lexeme(lex)
                return
            except Exception as e:
                print(f"⚠️ Warning loading sensory_dictionary.yaml: {e}")

        # Fallback to CANONICAL_LEXEMES
        for lex in CANONICAL_LEXEMES:
            self.add_lexeme(lex)

    def lookup(self, word_or_phrase: str) -> Optional[SensoryLexeme]:
        """O(1) exact surface form lookup for single words or multi-word phrases."""
        clean = word_or_phrase.lower().strip()
        words = [w for w in re.split(r"[\s\-]+", clean) if w]
        if not words:
            return None
        if len(words) == 1:
            return self.inverted_index.get(words[0])
        phrase_key = " ".join(words)
        return self.phrase_index.get(phrase_key)

    def match_longest_phrase(self, tokens: List[str], start_idx: int) -> Tuple[Optional[SensoryLexeme], int, str]:
        """
        Greedy Longest Match (Maximal Munch) starting at start_idx.
        Returns (SensoryLexeme, matched_length, matched_phrase_str) or (None, 0, '').
        """
        if self.max_phrase_len < 2 or start_idx >= len(tokens):
            return None, 0, ""

        limit = min(self.max_phrase_len, len(tokens) - start_idx)
        for n in range(limit, 1, -1):
            sub = tokens[start_idx : start_idx + n]
            cand = " ".join(sub)
            hit = self.phrase_index.get(cand)
            if hit:
                return hit, n, cand
        return None, 0, ""

    def _is_theme_compatible(self, lex: SensoryLexeme, theme: str) -> bool:
        t = theme.lower().strip()
        return t in lex.thematic_tags or "core" in lex.thematic_tags or "all" in lex.thematic_tags

    def get_synonyms(self, word_or_lemma: str, theme: Optional[str] = None, intensity: Optional[int] = None) -> List[SensoryLexeme]:
        """
        Retrieve synonyms for a word or lemma.
        - Tier 1: Explicit synonyms registered in lexeme.synonyms.
        - Tier 2 (Fallback): Semantic vector cluster (same senses + same thermal/tactile vector).
        Filters by theme and/or intensity if provided.
        """
        lex = self.lookup(word_or_lemma)
        results: List[SensoryLexeme] = []
        seen_lemmas: Set[str] = set()

        if lex:
            seen_lemmas.add(lex.lemma)
            # Tier 1: Explicit synonyms
            for syn in sorted(list(lex.synonyms)):
                syn_lex = self.lookup(syn)
                if syn_lex and syn_lex.lemma not in seen_lemmas:
                    if theme and not self._is_theme_compatible(syn_lex, theme):
                        continue
                    if intensity is not None and syn_lex.intensity != intensity:
                        continue
                    results.append(syn_lex)
                    seen_lemmas.add(syn_lex.lemma)

            # Tier 2 Fallback: If no explicit synonyms found, use semantic vector cluster
            if not results:
                for candidate in self.lexemes.values():
                    if candidate.lemma in seen_lemmas:
                        continue
                    if not any(s in lex.senses for s in candidate.senses):
                        continue
                    if lex.thermal and candidate.thermal != lex.thermal:
                        continue
                    if lex.tactile and candidate.tactile != lex.tactile:
                        continue
                    if theme and not self._is_theme_compatible(candidate, theme):
                        continue
                    if intensity is not None and candidate.intensity != intensity:
                        continue
                    results.append(candidate)
                    seen_lemmas.add(candidate.lemma)
                    if len(results) >= 8:
                        break

        return results

    def get_antonyms(self, word_or_lemma: str, theme: Optional[str] = None) -> List[SensoryLexeme]:
        """
        Retrieve antonyms (atmospheric counter-polarity pairs, bounded depth k=1).
        Filters by theme if provided.
        """
        lex = self.lookup(word_or_lemma)
        results: List[SensoryLexeme] = []
        seen_lemmas: Set[str] = set()

        if lex:
            seen_lemmas.add(lex.lemma)
            # Tier 1: Explicit antonyms
            for ant in sorted(list(lex.antonyms)):
                ant_lex = self.lookup(ant)
                if ant_lex and ant_lex.lemma not in seen_lemmas:
                    if theme and not self._is_theme_compatible(ant_lex, theme):
                        continue
                    results.append(ant_lex)
                    seen_lemmas.add(ant_lex.lemma)

            # Tier 2: Polar Vector Fallback (e.g. cold -> warm, hard -> soft)
            if not results:
                target_thermal = "warm" if lex.thermal == "cold" else ("cold" if lex.thermal == "warm" else None)
                target_tactile = "soft" if lex.tactile == "hard" else ("hard" if lex.tactile == "soft" else None)

                if target_thermal or target_tactile:
                    for candidate in self.lexemes.values():
                        if candidate.lemma in seen_lemmas:
                            continue
                        if target_thermal and candidate.thermal == target_thermal:
                            if theme and not self._is_theme_compatible(candidate, theme):
                                continue
                            results.append(candidate)
                            seen_lemmas.add(candidate.lemma)
                        elif target_tactile and candidate.tactile == target_tactile:
                            if theme and not self._is_theme_compatible(candidate, theme):
                                continue
                            results.append(candidate)
                            seen_lemmas.add(candidate.lemma)
                        if len(results) >= 6:
                            break

        return results

    def validate_graph_integrity(self) -> Dict[str, Any]:
        """Verify that all referenced synonyms and antonyms exist in the dictionary."""
        missing_synonyms: Dict[str, List[str]] = {}
        missing_antonyms: Dict[str, List[str]] = {}
        total_syn_links = 0
        total_ant_links = 0
        total_alias_links = 0

        for lex in self.lexemes.values():
            total_alias_links += len(lex.aliases)
            for syn in lex.synonyms:
                total_syn_links += 1
                if not self.lookup(syn):
                    missing_synonyms.setdefault(lex.lemma, []).append(syn)
            for ant in lex.antonyms:
                total_ant_links += 1
                if not self.lookup(ant):
                    missing_antonyms.setdefault(lex.lemma, []).append(ant)

        return {
            "valid": len(missing_synonyms) == 0 and len(missing_antonyms) == 0,
            "total_syn_links": total_syn_links,
            "total_ant_links": total_ant_links,
            "total_alias_links": total_alias_links,
            "missing_synonyms": missing_synonyms,
            "missing_antonyms": missing_antonyms
        }

    def get_lexemes_for_theme(self, theme: str) -> List[SensoryLexeme]:
        """Return all lexemes that are valid for a given theme."""
        t_clean = theme.lower().strip()
        matched = []
        for lex in self.lexemes.values():
            if self._is_theme_compatible(lex, t_clean):
                matched.append(lex)
        return matched

    def list_themes(self) -> Dict[str, int]:
        """Count lemmas available per theme."""
        counts = {t: 0 for t in self.themes_registry}
        for lex in self.lexemes.values():
            for t in lex.thematic_tags:
                counts[t] = counts.get(t, 0) + 1
        return counts

    def add_theme_to_lemma(self, lemma: str, theme: str) -> bool:
        """Allow an existing term to be used in another theme."""
        lex = self.lexemes.get(lemma.lower())
        if not lex:
            print(f"❌ Error: Lemma '{lemma}' not found in dictionary.")
            return False
        lex.thematic_tags.add(theme.lower().strip())
        self.save_yaml()
        print(f"✅ Added theme '{theme}' to lemma '{lemma}'! Active themes: {sorted(list(lex.thematic_tags))}")
        return True

    def save_yaml(self):
        try:
            import yaml
            doc = {
                "version": "2.1.0",
                "title": "Convergence Master Unified Sensory Dictionary (SSOT)",
                "description": "Single authoritative dictionary of sensory terms, irregular English inflections, and cross-thematic applications.",
                "themes_registry": self.themes_registry,
                "lexemes": [
                    l.to_dict()
                    for l in sorted(self.lexemes.values(), key=lambda x: x.lemma)
                ]
            }
            DICTIONARY_YAML_FILE.write_text(yaml.dump(doc, sort_keys=False, width=120), encoding="utf-8")
            return True
        except Exception as e:
            print(f"❌ Error saving sensory_dictionary.yaml: {e}")
            return False

# Global singleton instance
_GLOBAL_DICT: Optional[MasterSensoryDictionary] = None

def get_dictionary() -> MasterSensoryDictionary:
    global _GLOBAL_DICT
    if _GLOBAL_DICT is None:
        _GLOBAL_DICT = MasterSensoryDictionary()
    return _GLOBAL_DICT

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convergence Master Unified Sensory Dictionary CLI")
    parser.add_argument("--list-themes", action="store_true", help="List all registered themes and their active lemma counts")
    parser.add_argument("--query", "-q", help="Query a surface word or lemma to inspect its senses, forms, and allowed themes")
    parser.add_argument("--thesaurus", "-t", help="Explore synonyms (with intensity 1-3), counter-antonyms, and lore aliases")
    parser.add_argument("--theme", help="Filter thesaurus/query output by active thematic profile")
    parser.add_argument("--intensity", type=int, choices=[1, 2, 3], help="Filter synonyms by intensity scale (1: mild, 2: moderate, 3: severe)")
    parser.add_argument("--add-theme", nargs=2, metavar=("LEMMA", "THEME"), help="Attach an existing lemma to an additional theme")
    parser.add_argument("--validate-graph", action="store_true", help="Validate relational graph integrity (synonyms/antonyms)")
    args = parser.parse_args()

    d = get_dictionary()

    if args.validate_graph:
        print("\n" + "=" * 80)
        print("SENSORY KNOWLEDGE GRAPH: INTEGRITY VALIDATION")
        print("=" * 80)
        res = d.validate_graph_integrity()
        print(f"• Total Synonym Links Checked  : {res['total_syn_links']}")
        print(f"• Total Antonym Links Checked  : {res['total_ant_links']}")
        print(f"• Total Lore Aliases Indexed   : {res['total_alias_links']}")
        if res["valid"]:
            print("✅ 100% GRAPH INTEGRITY: All referenced synonyms and antonyms resolve cleanly!")
        else:
            if res["missing_synonyms"]:
                print("\n⚠️ Missing Synonym Targets:")
                for k, v in res["missing_synonyms"].items():
                    print(f"   • {k} -> {', '.join(v)}")
            if res["missing_antonyms"]:
                print("\n⚠️ Missing Antonym Targets:")
                for k, v in res["missing_antonyms"].items():
                    print(f"   • {k} -> {', '.join(v)}")
        print("=" * 80 + "\n")
        return

    if args.list_themes:
        print("\n" + "=" * 80)
        print("CONVERGENCE MASTER SENSORY DICTIONARY: THEMES REGISTRY")
        print("=" * 80)
        counts = d.list_themes()
        for t, desc in d.themes_registry.items():
            cnt = counts.get(t, 0)
            print(f"• {t:<22} ({cnt:>3} lemmas) : {desc}")
        print("=" * 80 + "\n")
        return

    if args.thesaurus:
        hit = d.lookup(args.thesaurus)
        if not hit:
            print(f"\n❌ Word '{args.thesaurus}' not found in Master Sensory Dictionary.\n")
            return
        theme_filter = args.theme
        intensity_filter = args.intensity
        syns = d.get_synonyms(args.thesaurus, theme=theme_filter, intensity=intensity_filter)
        ants = d.get_antonyms(args.thesaurus, theme=theme_filter)

        print(f"\n📚 SENSORY THESAURUS GRAPH: '{args.thesaurus}'")
        print(f"  • Canonical Lemma : {hit.lemma} (Intensity: {hit.intensity}/3)")
        print(f"  • Primary Senses  : {', '.join(hit.senses)}")
        print(f"  • Vectors         : Thermal: {hit.thermal or 'Neutral'} | Tactile: {hit.tactile or 'Neutral'}")
        if hit.aliases:
            print(f"  • In-Universe Lore: {', '.join(sorted(list(hit.aliases)))}")

        print("\n  🔍 SYNONYMS (Thematic & Intensity Clustered):")
        if syns:
            for s in syns:
                tag_str = ", ".join(sorted(list(s.thematic_tags)))
                int_label = {1: "1:Mild", 2: "2:Moderate", 3: "3:Severe"}.get(s.intensity, "2:Moderate")
                print(f"     • [{int_label}] {s.lemma:<16} (Senses: {', '.join(s.senses):<18} | Themes: [{tag_str}])")
        else:
            print("     (No direct synonyms found matching criteria)")

        print("\n  ⚖️  COUNTER-POLARITY / ANTONYMS (Dynamic Contrast):")
        if ants:
            for a in ants:
                tag_str = ", ".join(sorted(list(a.thematic_tags)))
                print(f"     • {a.lemma:<16} (Thermal: {a.thermal or 'Neutral':<5} | Tactile: {a.tactile or 'Neutral':<5} | Themes: [{tag_str}])")
        else:
            print("     (No counter-polarities found matching criteria)")
        print("=" * 80 + "\n")
        return

    if args.add_theme:
        lemma, theme = args.add_theme
        d.add_theme_to_lemma(lemma, theme)
        return

    if args.query:
        hit = d.lookup(args.query)
        if hit:
            print(f"\n📖 SENSORY DICTIONARY ENTRY: '{args.query}'")
            print(f"  • Canonical Lemma : {hit.lemma}")
            print(f"  • Senses Triggered: {', '.join(hit.senses)}")
            print(f"  • Part of Speech  : {hit.pos}")
            print(f"  • Intensity Level : {hit.intensity}/3")
            print(f"  • Allowed Themes  : {', '.join(sorted(list(hit.thematic_tags)))}")
            print(f"  • Thermal Vector  : {hit.thermal or 'Neutral'}")
            print(f"  • Tactile Vector  : {hit.tactile or 'Neutral'}")
            if hit.synonyms:
                print(f"  • Direct Synonyms : {', '.join(sorted(list(hit.synonyms)))}")
            if hit.antonyms:
                print(f"  • Counter Antonyms: {', '.join(sorted(list(hit.antonyms)))}")
            if hit.aliases:
                print(f"  • Lore Aliases    : {', '.join(sorted(list(hit.aliases)))}")
            print(f"  • Inflected Forms : {', '.join(sorted(list(hit.forms)))}\n")
        else:
            print(f"\n❌ Word '{args.query}' not found in Master Sensory Dictionary.\n")
        return

    print("=" * 70)
    print("CONVERGENCE STUDIO: MASTER UNIFIED SENSORY DICTIONARY (SSOT)")
    print("=" * 70)
    print(f"• Total Canonical Lemmas         : {len(d.lexemes)}")
    print(f"• Indexed Single-Word Forms (O(1)): {len(d.inverted_index)}")
    print(f"• Indexed Multi-Word Phrases     : {len(d.phrase_index)}")
    print(f"• Max Phrase Length              : {d.max_phrase_len} words")
    print(f"• Registered Thematic Profiles   : {len(d.themes_registry)}")
    print("-" * 70)

    # Test some cross-thematic and compound queries
    test_words = ["steam", "copper", "cider", "froze", "ground", "cold-rolled", "death-rattle"]
    print("Cross-Thematic & Compound Surface Queries:")
    for tw in test_words:
        hit = d.lookup(tw)
        if hit:
            themes_str = ", ".join(sorted(list(hit.thematic_tags)))
            print(f"  ✓ '{tw:<14}' -> Lemma: '{hit.lemma:<14}' | Senses: {hit.senses} | Themes: [{themes_str}]")
    print("=" * 70)

if __name__ == "__main__":
    main()

