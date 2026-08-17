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

            # Synthetic/real policy documents often refer to the old policy by a
            # longer title than the stored filename. Match by partner + version,
            # not by exact filename text.
            targets = re.findall(r"supersedes\s+([^\.\n]+)", content, re.IGNORECASE)
            for target in targets:
                target_version = self._policy_version(target)
                target_norm = self._normalized_name(target)
                current_norm = self._normalized_name(current_name)
                for other in results:
                    other_name = other.get("document_name", "")
                    if other_name == current_name:
                        continue
                    other_norm = self._normalized_name(other_name)
                    if target_version is not None and self._policy_version(other_name) == target_version:
                        # Require a meaningful shared policy/partner identity.
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
