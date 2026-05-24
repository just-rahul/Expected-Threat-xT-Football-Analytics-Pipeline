"""Quick API test — uploads CSV and prints results."""
import requests
import json
import sys

csv_path = sys.argv[1] if len(sys.argv) > 1 else "test_transactions.csv"
url = "http://localhost:8000/api/analyze"

print(f"Uploading {csv_path} to {url}...")
with open(csv_path, "rb") as f:
    resp = requests.post(url, files={"file": (csv_path, f, "text/csv")})

if resp.status_code != 200:
    print(f"ERROR: status {resp.status_code}")
    print(resp.text)
    sys.exit(1)

data = resp.json()
result = data["result"]
graph = data["graph"]
summary = result["summary"]

print(f"\n=== Analysis Summary ===")
print(json.dumps(summary, indent=2))
print(f"\nGraph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
print(f"Suspicious accounts: {len(result['suspicious_accounts'])}")
print(f"Fraud rings: {len(result['fraud_rings'])}")

if result["fraud_rings"]:
    print("\nFraud Rings:")
    for ring in result["fraud_rings"]:
        print(f"  {ring['ring_id']}  type={ring['pattern_type']}  members={len(ring['member_accounts'])}  risk={ring['risk_score']}")

print("\nAll OK!")
