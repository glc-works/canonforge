"""
dictionary.py

Authoritative lexicographic data structure and O(1) inverted lookup index
for literary sensory analysis. Handles:
1. Explicit irregular English inflections (froze -> freeze, ground -> grind, etc.)
2. Morphological form expansion (plurals, participles, past tenses, adjectival derivations)
3. Multi-sensory tagging (e.g. 'cider' -> taste + smell; 'scald' -> touch + thermal hot)
4. Atmospheric vectors (Thermal: Warm vs Cold, Tactile: Hard vs Soft)
"""

import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PACKAGE_ROOT / "data"
DICTIONARY_JSON_FILE = DATA_DIR / "sensory_dictionary.json"

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

class SensoryDictionary:
    def __init__(self, json_file: Optional[Path] = None):
        self.json_file = json_file or DICTIONARY_JSON_FILE
        self.lexemes: Dict[str, SensoryLexeme] = {}
        self.inverted_index: Dict[str, SensoryLexeme] = {}
        self.phrase_index: Dict[str, SensoryLexeme] = {}
        self.themes_registry: Dict[str, str] = {}
        self.max_phrase_len: int = 1
        self._load()

    def add_lexeme(self, lex: SensoryLexeme):
        self.lexemes[lex.lemma] = lex
        for f in lex.forms:
            words = [w for w in re.split(r"[\s\-]+", f) if w]
            if len(words) == 1:
                self.inverted_index[words[0]] = lex
            elif len(words) > 1:
                phrase_key = " ".join(words)
                self.phrase_index[phrase_key] = lex
                if len(words) > self.max_phrase_len:
                    self.max_phrase_len = len(words)
        for alias in lex.aliases:
            alias_clean = alias.lower().strip()
            words = [w for w in re.split(r"[\s\-]+", alias_clean) if w]
            if len(words) == 1:
                self.inverted_index[words[0]] = lex
            elif len(words) > 1:
                phrase_key = " ".join(words)
                self.phrase_index[phrase_key] = lex
                if len(words) > self.max_phrase_len:
                    self.max_phrase_len = len(words)

    def _load(self):
        if self.json_file.is_file():
            try:
                data = json.loads(self.json_file.read_text(encoding="utf-8"))
                self.themes_registry = data.get("themes_registry", {})
                for item in data.get("lexemes", []):
                    lex = SensoryLexeme.from_dict(item)
                    self.add_lexeme(lex)
                return
            except Exception as e:
                print(f"Warning: Failed loading JSON sensory dictionary: {e}", file=sys.stderr)

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
        """Greedy Longest Match (Maximal Munch) starting at start_idx."""
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

    def get_lexemes_for_theme(self, theme: str) -> List[SensoryLexeme]:
        """Return all lexemes that are valid for a given theme."""
        t_clean = theme.lower().strip()
        matched = []
        for lex in self.lexemes.values():
            if self._is_theme_compatible(lex, t_clean):
                matched.append(lex)
        return matched

    def get_synonyms(self, word_or_lemma: str, theme: Optional[str] = None, intensity: Optional[int] = None) -> List[SensoryLexeme]:
        """Retrieve synonyms for a word or lemma."""
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

            # Tier 2: Semantic cluster fallback
            if len(results) < 3:
                for candidate in self.lexemes.values():
                    if candidate.lemma in seen_lemmas:
                        continue
                    if set(candidate.senses) == set(lex.senses):
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
        """Retrieve antonyms (atmospheric counter-polarity pairs, bounded depth k=1)."""
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

            # Tier 2: Polar Vector Fallback
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

_GLOBAL_DICT: Optional[SensoryDictionary] = None

def get_dictionary() -> SensoryDictionary:
    """Singleton getter for the high-performance master sensory dictionary."""
    global _GLOBAL_DICT
    if _GLOBAL_DICT is None:
        _GLOBAL_DICT = SensoryDictionary()
    return _GLOBAL_DICT
