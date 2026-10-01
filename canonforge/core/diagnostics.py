"""
CanonForge: Standardized Diagnostic Codes & LSP-Ready Diagnostic Model
--------------------------------------------------------------------------------
Benchmarked against Ruff (astral-sh/ruff) and ESLint.
Enables structured, editor-agnostic diagnostics for VS Code, Obsidian, and CI.
"""

from enum import Enum
from typing import Dict, Any, Optional

class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"

class DiagnosticCode(str, Enum):
    # POV Rules (POV001 - POV099)
    POV_HEAD_HOPPING = "POV001"          # Non-POV interiority / mental state leak
    POV_MISSING_DECLARATION = "POV002"   # Missing POV field in frontmatter
    POV_UNCLEAR_TRANSITION = "POV003"    # Multi-POV without clear section break

    # Anti-Slop & Prose Purity Rules (SLOP001 - SLOP099)
    SLOP_AI_CLICHE = "SLOP001"           # Forbidden AI prose cliché or purple metaphor
    SLOP_TRICOLON = "SLOP002"            # Predictable tricolon pattern ('not X, but Y, a Z')
    SLOP_FILTER_WORD = "SLOP003"         # Cognitive filter word dampening Deep POV
    SLOP_DIALOGUE_ADVERB = "SLOP004"     # Cluttered dialogue adverb vs subtext/action

    # Sensory Immersion Rules (SEN001 - SEN099)
    SEN_WINDOW_DEFICIT = "SEN001"        # < 3 senses active in 500-word window
    SEN_UNMAPPED_LEMMA = "SEN002"        # Word missing from sensory graph
    SEN_ATMOSPHERE_IMBALANCE = "SEN003"  # Thermal or tactile polarity conflict

    # Chronology & Physics Rules (CHRON001 - CHRON099)
    CHRON_TRANSIT_VELOCITY = "CHRON001"  # Impossible travel transit speed
    CHRON_TEMPORAL_REGRESSION = "CHRON002" # Chapter timeline regresses backwards

    # Epistemic & Continuity Rules (EPIST001 - EPIST099)
    EPIST_SECRET_LEAK = "EPIST001"       # Character speaks of unrevealed secret
    EPIST_ORPHAN_CHARACTER = "EPIST002"  # Character mentioned not in lore/cast

    # Structural Integrity (TOC001 - TOC099)
    TOC_ORPHAN_FILE = "TOC001"           # File exists on disk but missing from TOC
    TOC_MISSING_FILE = "TOC002"          # TOC lists chapter file that does not exist
    SCHEMA_VIOLATION = "SCHEMA001"       # Frontmatter fails OKF v0.3 schema

class Diagnostic:
    """Represents an atomic diagnostic finding in a manuscript file."""
    def __init__(
        self,
        code: DiagnosticCode,
        message: str,
        severity: Severity = Severity.WARNING,
        line: int = 1,
        column: int = 1,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
        context: str = "",
        fix_suggestion: str = "",
        source_engine: str = "canonforge"
    ):
        self.code = code if isinstance(code, DiagnosticCode) else DiagnosticCode(code)
        self.message = message
        self.severity = severity if isinstance(severity, Severity) else Severity(severity)
        self.line = line
        self.column = column
        self.end_line = end_line or line
        self.end_column = end_column or column
        self.context = context
        self.fix_suggestion = fix_suggestion
        self.source_engine = source_engine

    def to_dict(self) -> Dict[str, Any]:
        """Convert to LSP-compatible dictionary."""
        return {
            "code": self.code.value,
            "rule": self.code.name,
            "severity": self.severity.value,
            "message": self.message,
            "range": {
                "start": {"line": self.line, "character": self.column},
                "end": {"line": self.end_line, "character": self.end_column}
            },
            "context": self.context,
            "fix": self.fix_suggestion,
            "source": self.source_engine
        }

    def __repr__(self) -> str:
        return f"<{self.code.value} [{self.severity.value.upper()}] Line {self.line}: {self.message}>"
