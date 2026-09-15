"""Pharos — a lighthouse for drug safety.

Two modes:
  * Signal detection  — disproportionality analysis (PRR / ROR / chi-square) over
                        real FDA FAERS adverse-event data via the openFDA API.
  * Submission readiness — checks a drug-approval dossier outline against the
                        ICH M4 Common Technical Document (CTD) structure.

The package is the *evidence layer*. IBM Bob, connected through the MCP server in
``src/mcp_server``, is the *reasoning layer* that turns evidence into narrative.
"""

__version__ = "0.1.0"
