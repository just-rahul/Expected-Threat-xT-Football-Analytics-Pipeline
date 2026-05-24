"""Precision validation for gated fraud architecture."""
import pandas as pd
from engine import ForensicsEngine

e = ForensicsEngine()
e.load_data(pd.read_csv("../test_transactions.csv"))
r = e.run_all()
accs = r["suspicious_accounts"]
rings = r["fraud_rings"]

print(f"Flagged: {len(accs)}")
print(f"Rings: {len(rings)}")
print()

for a in accs:
    print(f"  {a['account_id']}  score={a['suspicion_score']}  "
          f"patterns={a['detected_patterns']}  ring={a['ring_id']}")
    print(f"    explanation: {a['explanation']}")

print()

# Check 1: Zero payroll/merchant false positives
fp = [a for a in accs if "payroll" in a["detected_patterns"]
      or "merchant" in a["detected_patterns"]]
print(f"Payroll/Merchant FP: {len(fp)} (must be 0)  {'PASS' if len(fp) == 0 else 'FAIL'}")

# Check 2: No smurf rings with <4 members
small = [r2 for r2 in rings
         if r2["pattern_type"] == "smurfing" and len(r2["member_accounts"]) < 4]
print(f"Small smurf rings:  {len(small)} (must be 0)  {'PASS' if len(small) == 0 else 'FAIL'}")

# Check 3: No accounts flagged with ONLY velocity
vel_only = [a for a in accs if a["detected_patterns"] == ["high_velocity"]]
print(f"Velocity-only flags: {len(vel_only)} (must be 0)  {'PASS' if len(vel_only) == 0 else 'FAIL'}")

# Check 4: All scores >= FLAG_THRESHOLD (25)
below = [a for a in accs if a["suspicion_score"] < 25]
print(f"Below threshold:    {len(below)} (must be 0)  {'PASS' if len(below) == 0 else 'FAIL'}")

# Check 5: Ring IDs unique
ring_ids = [r2["ring_id"] for r2 in rings]
print(f"Unique ring IDs:    {len(set(ring_ids))}/{len(ring_ids)}  "
      f"{'PASS' if len(set(ring_ids)) == len(ring_ids) else 'FAIL'}")

# Check 6: No null ring_ids in rings
null_ids = [r2 for r2 in rings if not r2["ring_id"]]
print(f"Null ring IDs:      {len(null_ids)} (must be 0)  {'PASS' if len(null_ids) == 0 else 'FAIL'}")

print()
print("All rings:")
for r2 in rings:
    print(f"  {r2['ring_id']}  type={r2['pattern_type']}  "
          f"members={len(r2['member_accounts'])}  risk={r2['risk_score']}")

# Summary
all_pass = (len(fp) == 0 and len(small) == 0 and len(vel_only) == 0
            and len(below) == 0 and len(set(ring_ids)) == len(ring_ids)
            and len(null_ids) == 0)
print(f"\n{'='*40}")
print(f"  ALL CHECKS {'PASSED' if all_pass else 'FAILED'}")
print(f"{'='*40}")
