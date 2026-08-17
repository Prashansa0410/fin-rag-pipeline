from typing import List, Dict, Any, Tuple
import re


class RetrievalConfidenceAnalyzer:
    def __init__(self):
        self.conflict_patterns = [r"t\+[0-9]+", r"[0-9]+ days", r"[0-9]+ hours"]

    def analyze_confidence(self, results: List[Dict[str, Any]]) -> Tuple[float, str, bool, List[Dict[str, Any]]]:
        if not results:
            return 0.0, "LOW", False, []

        # Enforce source diversity: no more than 3 chunks from one document in the evidence set.
        counts: Dict[str, int] = {}
        diverse_results = []
        for res in results:
            doc_name = res.get("document_name", "unknown")
            if counts.get(doc_name, 0) >= 3:
                continue
            counts[doc_name] = counts.get(doc_name, 0) + 1
            diverse_results.append(res)

        has_conflict = False
        partner_doc_rules: Dict[str, Dict[str, set]] = {}
        for res in diverse_results[:8]:
            doc_name = res.get("document_name", "").lower()
            if any(word in doc_name for word in ("incident", "recon", "summary", "report")):
                continue
            content = res.get("content", "").lower()
            metadata = res.get("metadata") or {}
            partner = str(metadata.get("partner") or res.get("partner") or "global").lower()
            for pattern in self.conflict_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    partner_doc_rules.setdefault(partner, {}).setdefault(doc_name, set()).update(matches)

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
