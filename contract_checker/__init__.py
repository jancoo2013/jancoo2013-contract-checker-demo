"""Public-safe contract checker demo package."""

from .models import CheckFinding, CheckResult
from .pipeline import analyze_contract_text

__all__ = ["CheckFinding", "CheckResult", "analyze_contract_text"]
