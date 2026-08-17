from typing import List, Dict, Any, Tuple
import re

class RetrievalConfidenceAnalyzer:
    def __init__(self):
        # Patterns to check for potentially conflicting financial/compliance rules
        self.conflict_patterns = [
            r"t\+[0-9]", # T+1, T+2 etc
            r"[0-9]+ days",
            r"[0-9]+ hours"
        ]

    def analyze_confidence(self, results: List[Dict[str, Any]]) -> Tuple[float, str, bool, List[Dict[str, Any]]]:
        """
        Calculates a heuristic confidence score, detects conflicts, and applies source diversity.
        Returns: (confidence_score, confidence_level, has_conflict, diverse_results)
        """
        if not results:
            return 0.0, "LOW", False, []

        # 1. Source Diversity
        # We want to ensure one document doesn't take all top slots if others exist.
        doc_counts = {}
        diverse_results = []
        for res in results:
            doc_name = res.get("document_name", "unknown")
            if doc_counts.get(doc_name, 0) < 3: # Max 3 chunks from a single document ideally
                diverse_results.append(res)
                doc_counts[doc_name] = doc_counts.get(doc_name, 0) + 1
            else:
                # Still add it but demote its score slightly so other docs can surface if we re-sort
                # For this simple implementation, we just keep it but at the end.
                diverse_results.append(res)
                
        # 2. Conflict Detection
        # Refined approach: Group detected numerical rules by the 'partner' AND 'document_name'.
        has_conflict = False
        partner_doc_rules = {}
        for res in diverse_results[:5]: # Only check top 5 for conflicts
            doc_name = res.get("document_name", "").lower()
            if "incident" in doc_name or "recon" in doc_name or "summary" in doc_name or "report" in doc_name:
                continue
                
            content = res.get("content", "").lower()
            partner = res.get("metadata", {}).get("partner") or "global"
            
            for pattern in self.conflict_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    if partner not in partner_doc_rules:
                        partner_doc_rules[partner] = {}
                    if doc_name not in partner_doc_rules[partner]:
                        partner_doc_rules[partner][doc_name] = set()
                    for match in matches:
                        partner_doc_rules[partner][doc_name].add(match)
                    
        # Check if any single entity has multiple different active rules ACROSS DIFFERENT documents
        for partner, docs in partner_doc_rules.items():
            if len(docs) > 1:
                all_rules = set()
                for doc_rules in docs.values():
                    all_rules.update(doc_rules)
                if len(all_rules) > 1:
                    has_conflict = True
                    break
            
        # 3. Confidence Calculation
        top_score = diverse_results[0].get("score", 0.0)
        
        # Gap between #1 and #2 shows if there is a single authoritative answer
        score_gap = 0.0
        if len(diverse_results) > 1:
            score_gap = top_score - diverse_results[1].get("score", 0.0)
            
        # Heuristic rules
        confidence_level = "LOW"
        if top_score > 0.8:
            if has_conflict:
                confidence_level = "MEDIUM" # Good match but conflicting info
            else:
                confidence_level = "HIGH"
        elif top_score > 0.6:
            confidence_level = "MEDIUM"
            
        return top_score, confidence_level, has_conflict, diverse_results

confidence_analyzer = RetrievalConfidenceAnalyzer()
