import re
from typing import Dict, Any

class QueryAnalyzer:
    def __init__(self):
        # Very simple rules for deterministic extraction.
        # In a real app we could use spacy or a tiny local NER model.
        self.partner_patterns = [r"Partner [A-Z]", r"Partner [0-9]"]
        self.months = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        self.domains = ["Settlement", "Compliance", "Reconciliation", "Operations"]

    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Deterministically extracts metadata to avoid expensive LLM calls.
        """
        filters = {}
        
        # 1. Partner extraction
        for pattern in self.partner_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                # Normalize partner name (e.g. "Partner A")
                filters["partner"] = match.group(0).title()
                
        # 2. Date extraction (naive)
        for month in self.months:
            if month.lower() in query.lower():
                # We can map this to an effective_date range in hybrid search
                filters["month"] = month
                
        # 3. Domain extraction
        for domain in self.domains:
            if domain.lower() in query.lower():
                filters["business_domain"] = domain
                
        # 4. Query Complexity / Type heuristics
        is_high_risk = "compliance" in query.lower() or "violate" in query.lower() or "audit" in query.lower()
        is_comparison = "compare" in query.lower() or "difference" in query.lower()
        
        query_type = "UNKNOWN"
        if is_high_risk:
            query_type = "HIGH_RISK"
        elif is_comparison:
            query_type = "COMPARISON"
        else:
            first_word = query.lower().split()[0] if query else ""
            if first_word in ["what", "when", "who", "where", "how", "is", "does"]:
                query_type = "SIMPLE_FACT"
            
        # If it's a comparison query, do not restrict strictly to a single partner
        if is_comparison and "partner" in filters:
            del filters["partner"]
            
        return {
            "filters": filters,
            "query_type": query_type,
            "is_high_risk": is_high_risk,
            "is_comparison": is_comparison
        }

query_analyzer = QueryAnalyzer()
