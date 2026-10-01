"""
CanonForge: Unified Domain Exception Hierarchy
--------------------------------------------------------------------------------
Provides structured, catchable exceptions across all literary engines.
Engines must raise these domain errors rather than calling sys.exit().
"""

class CanonForgeError(Exception):
    """Base exception for all CanonForge errors."""
    pass

class ManifestError(CanonForgeError):
    """Raised when universe.yaml, series.yaml, or toc.yaml is invalid or missing."""
    pass

class ChapterNotFoundError(CanonForgeError):
    """Raised when a specified chapter file cannot be located."""
    pass

class ValidationError(CanonForgeError):
    """Raised when OKF v0.3 schema validation fails."""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []

class POVIntegrityError(CanonForgeError):
    """Raised when severe head-hopping or POV violation is detected."""
    pass

class SensoryComplianceError(CanonForgeError):
    """Raised when a chapter fails the 3-sense compliance threshold."""
    pass

class ChronologyError(CanonForgeError):
    """Raised when travel physics or timeline sequence regression occurs."""
    pass

class EpistemicLeakError(CanonForgeError):
    """Raised when premature secret revelation or plot spoilers occur."""
    pass
