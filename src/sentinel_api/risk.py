from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RiskAssessment:
    score: int
    level: str
    factors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_pull_request(payload: dict[str, Any]) -> RiskAssessment:
    """Explainable heuristic score; not a security verdict or merge decision."""
    score = 0
    factors: list[str] = []
    pr = payload.get("pull_request") or {}
    title = str(pr.get("title") or "").lower()
    body = str(pr.get("body") or "").lower()
    # GitHub's pull_request webhook nests these counters inside pull_request.
    changed_files = pr.get("changed_files", payload.get("changed_files"))
    additions = pr.get("additions", payload.get("additions"))
    deletions = pr.get("deletions", payload.get("deletions"))
    raw_labels = pr.get("labels", [])
    labels = {str(x.get("name", "")).lower() for x in raw_labels if isinstance(x, dict)} if isinstance(raw_labels, list) else set()

    if any(word in title for word in ("auth", "permission", "secret", "payment", "security")):
        score += 25
        factors.append("Sensitive topic in pull-request title")
    if any(word in body for word in ("migration", "breaking change", "production")):
        score += 15
        factors.append("Potentially high-impact change described")
    if isinstance(changed_files, int) and changed_files > 20:
        score += 20
        factors.append("Large change set (>20 files)")
    if isinstance(additions, int) and additions > 500:
        score += 15
        factors.append("Large additions (>500 lines)")
    if isinstance(deletions, int) and deletions > 300:
        score += 10
        factors.append("Large deletions (>300 lines)")
    if labels.intersection({"hotfix", "urgent"}):
        score += 10
        factors.append("Urgency label present")

    score = min(score, 100)
    level = "high" if score >= 60 else "medium" if score >= 30 else "low"
    if not factors:
        factors.append("No configured risk signals detected")
    return RiskAssessment(score=score, level=level, factors=factors)
