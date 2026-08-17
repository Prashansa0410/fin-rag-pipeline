import json
import httpx
import time
import os
import sys

def run_evaluation():
    eval_file = "data/evaluation/questions.json"
    if not os.path.exists(eval_file):
        print(f"Evaluation file not found: {eval_file}")
        sys.exit(1)

    with open(eval_file, "r") as f:
        questions = json.load(f)

    results = []
    
    print(f"Starting evaluation of {len(questions)} questions...\n")
    
    with httpx.Client(timeout=60.0) as client:
        for i, q in enumerate(questions):
            question = q["question"]
            expected_sources = set(q.get("expected_sources", []))
            expected_tier = q.get("expected_model_tier")
            expected_risk = q.get("expected_risk")
            expected_review = q.get("expected_review", False)
            
            print(f"[{i+1}/{len(questions)}] Q: {question}")
            
            start_time = time.time()
            try:
                response = client.post("http://127.0.0.1:8000/api/research/", json={
                    "query": question,
                    "user_id": "1e235958-1790-4289-a4d0-ace1ecb8e457",
                    "organization_id": "05a23510-ce14-4250-85d4-e2b9d6e7cbba"
                })
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                print(f"  Error querying API: HTTP {e.response.status_code} - {error_detail}")
                results.append({"question": question, "pass": False, "error": error_detail})
                continue
            except Exception as e:
                print(f"  Error querying API: {e}")
                results.append({"question": question, "pass": False, "error": str(e)})
                continue
                
            latency = time.time() - start_time
            
            actual_tier = data.get("selected_model_tier")
            retrieved_sources = set([c["source_id"] for c in data.get("citations", [])])
            requires_review = data.get("requires_review", False)
            
            # Check source overlap
            sources_matched = expected_sources.issubset(retrieved_sources)
            
            passed = sources_matched and (actual_tier == expected_tier) and (requires_review == expected_review)
            
            print(f"  Tier: Expected {expected_tier}, Actual {actual_tier}")
            print(f"  Review: Expected {expected_review}, Actual {requires_review}")
            print(f"  Sources matched: {sources_matched} (Expected: {expected_sources}, Actual: {retrieved_sources})")
            print(f"  Result: {'PASS' if passed else 'FAIL'}\n")
            
            results.append({
                "question": question,
                "expected_sources": list(expected_sources),
                "actual_sources": list(retrieved_sources),
                "expected_tier": expected_tier,
                "actual_tier": actual_tier,
                "expected_review": expected_review,
                "actual_review": requires_review,
                "latency_sec": round(latency, 2),
                "pass": passed
            })
            
    passed_count = sum(1 for r in results if r["pass"])
    print(f"\nEvaluation Complete: {passed_count}/{len(questions)} passed.")

if __name__ == "__main__":
    run_evaluation()
