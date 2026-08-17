from typing import List, Dict, Any, Tuple
import re


class RetrievalConfidenceAnalyzer:
    def __init__(self):
        self.conflict_patterns = [r"t\+[0-9]+", r"[0-9]+ days", r"[0-9]+ hours"]

    @staticmethod
    def _normalized_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()

    def _superseded_documents(self, results: List[Dict[str, Any]]) -> set[str]:
        """Find documents explicitly superseded by a newer policy/version."""
        superseded: set[str] = set()
        names = {self._normalized_name(r.get("document_name", "")): r.get("document_name", "") for r in results}
        for res in results:
            content = res.get("content", "")
            current_name = res.get("document_name", "")
            for match in re.findall(r"supersedes\s+([^\.\n]+)", content, re.IGNORECASE):
                target = self._normalized_name(match)
                for normalized, original in names.items():
                    if target and (target in normalized or normalized in target):
                        if original != current_name:
                            superseded.add(original)
        return superseded

    def analyze_confidence(self, results: List[Dict[str, Any]]) -> Tuple[float, str, bool, List[Dict[str, Any]]]:
        if not results:
            return 0.0, "LOW", False, []

        # Enforce source diversity: no more than 3 chunks from one document.
        counts: Dict[str, int] = {}
        diverse_results = []
        for res in results:
            doc_name = res.get("document_name", "unknown")
            if counts.get(doc_name, 0) >= 3:
                continue
            counts[doc_name] = counts.get(doc_name, 0) + 1
            diverse_results.append(res)

        # Version supersession is not a conflict. A newer policy explicitly saying it
        # supersedes an older policy should cause the older policy to be ignored for
        # contradiction analysis, while still allowing it to be returned as provenance.
        superseded_docs = self._superseded_documents(diverse_results)

        has_conflict = False
        partner_doc_rules: Dict[str, Dict[str, set]] = {}
        for res in diverse_results[:8]:
            doc_name = res.get("document_name", "")
            if doc_name in superseded_docs:
                continue
            lowered_name = doc_name.lower()
            if any(word in lowered_name for word in ("incident", "recon", "summary", "report")):
                continue
            content = res.get("content", "").lower()
            metadata = res.get("metadata") or {}
            partner = str(metadata.get("partner") or res.get("partner") or "global").lower()
            for pattern in self.conflict_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    partner_doc_rules.setdefault(partner, {}).setdefault(doc_name, set()).update(matches)

        # Only compare rules within the same partner/scope. Partner A T+1 vs Partner B
        # T+2 is expected policy variation, not contradictory evidence.
        for docs in partner_doc_rules.values():
            if len(docs) > 1:
                all_rules = set().union(*docs.values())
                if len(all_rules) > 1:
                    has_conflict = True
                    break

        top_score = float(diverse_results[0].get("score", 0.0)) if diverse_results else 0.0
        if top_score > 0.8 and not has_conflict:
            confidence_level = "HIGH"
        elif top_score > 0.6:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"
        if has_conflict:
            confidence_level = "MEDIUM"

        return top_score, confidence_level, has_conflict, diverse_results


confidence_analyzer = RetrievalConfidenceAnalyzer()
