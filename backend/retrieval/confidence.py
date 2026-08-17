from typing import List, Dict, Any, Tuple
import re


class RetrievalConfidenceAnalyzer:
    def __init__(self):
        self.conflict_patterns = [r"t\+[0-9]+", r"[0-9]+ days", r"[0-9]+ hours"]

    @staticmethod
    def _normalized_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()

    @staticmethod
    def _policy_version(name: str):
        match = re.search(r"(?:^|[_\s-])v(\d+)(?:\.|[_\s-]|$)", name.lower())
        return int(match.group(1)) if match else None

    def _superseded_documents(self, results: List[Dict[str, Any]]) -> set[str]:
        superseded: set[str] = set()
        for res in results:
            content = res.get("content", "")
            current_name = res.get("document_name", "")
            if not re.search(r"supersedes\s+", content, re.IGNORECASE):
                continue
            targets = re.findall(r"supersedes\s+([^\.\n]+)", content, re.IGNORECASE)
            for target in targets:
                target_version = self._policy_version(target)
                target_norm = self._normalized_name(target)
                for other in results:
                    other_name = other.get("document_name", "")
                    if other_name == current_name:
                        continue
                    other_norm = self._normalized_name(other_name)
                    if target_version is not None and self._policy_version(other_name) == target_version:
                        target_tokens = set(target_norm.split())
                        other_tokens = set(other_norm.split())
                        if ("partner" in target_tokens and "partner" in other_tokens) or "policy" in other_tokens:
                            superseded.add(other_name)
                    elif target_norm and (target_norm in other_norm or other_norm in target_norm):
                        superseded.add(other_name)
        return superseded

    def analyze_confidence(self, results: List[Dict[str, Any]]) -> Tuple[float, str, bool, List[Dict[str, Any]]]:
        if not results:
            return 0.0, "LOW", False, []

        counts: Dict[str, int] = {}
        diverse_results = []
        for res in results:
            doc_name = res.get("document_name", "unknown")
            if counts.get(doc_name, 0) >= 3:
                continue
            counts[doc_name] = counts.get(doc_name, 0) + 1
            diverse_results.append(res)

        superseded_docs = self._superseded_documents(diverse_results)
        evidence = [r for r in diverse_results if r.get("document_name") not in superseded_docs]

        has_conflict = False
        partner_doc_rules: Dict[str, Dict[str, set]] = {}
        for res in evidence[:8]:
            doc_name = res.get("document_name", "")
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

        for docs in partner_doc_rules.values():
            if len(docs) > 1 and len(set().union(*docs.values())) > 1:
                has_conflict = True
                break

        top = float(evidence[0].get("score", 0.0)) if evidence else 0.0
        second = float(evidence[1].get("score", 0.0)) if len(evidence) > 1 else 0.0
        margin = max(0.0, min(1.0, top - second))
        lexical = float(evidence[0].get("lexical_score", 0.0)) if evidence else 0.0
        filename = float(evidence[0].get("filename_score", 0.0)) if evidence else 0.0
        phrase = float(evidence[0].get("phrase_score", 0.0)) if evidence else 0.0
        source_concentration = 1.0 / len({r.get("document_name") for r in evidence}) if evidence else 0.0

        confidence = min(1.0, (
            0.45 * min(1.0, top) +
            0.20 * lexical +
            0.10 * filename +
            0.10 * phrase +
            0.10 * margin +
            0.05 * source_concentration
        ))
        if has_conflict:
            confidence *= 0.75

        if has_conflict:
            level = "MEDIUM"
        elif confidence >= 0.70 or (top >= 0.65 and lexical >= 0.70 and margin >= 0.08):
            level = "HIGH"
        elif confidence >= 0.48:
            level = "MEDIUM"
        else:
            level = "LOW"

        return confidence, level, has_conflict, evidence


confidence_analyzer = RetrievalConfidenceAnalyzer()
