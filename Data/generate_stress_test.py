import csv
import random
from datetime import datetime, timedelta

random.seed(42)

TOTAL_TRANSACTIONS = 5000
TOTAL_ACCOUNTS = 200
ACCOUNTS = [f"A{i:04d}" for i in range(1, TOTAL_ACCOUNTS + 1)]
BASE_TIME = datetime(2024, 1, 1, 0, 0, 0)
SPAN_DAYS = 30
OUTPUT_FILE = "stress_test.csv"

txn_counter = 0

def next_txn_id():
    global txn_counter
    txn_counter += 1
    return f"TXN{txn_counter:06d}"

def rand_ts():
    offset = random.uniform(0, SPAN_DAYS * 86400)
    return BASE_TIME + timedelta(seconds=offset)

def fmt(ts):
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def generate_normal(count, used_accounts):
    rows = []
    pool = [a for a in ACCOUNTS if a not in used_accounts]
    for _ in range(count):
        s = random.choice(pool)
        r = random.choice(pool)
        while r == s:
            r = random.choice(pool)
        amount = round(random.uniform(50, 5000), 2)
        rows.append([next_txn_id(), s, r, amount, fmt(rand_ts())])
    return rows

def generate_cycles(num_cycles, used_accounts):
    rows = []
    available = [a for a in ACCOUNTS if a not in used_accounts]
    random.shuffle(available)
    for i in range(num_cycles):
        a, b, c = available[i * 3], available[i * 3 + 1], available[i * 3 + 2]
        used_accounts.update([a, b, c])
        base_amount = round(random.uniform(2000, 8000), 2)
        base_ts = BASE_TIME + timedelta(days=random.randint(1, 25))
        rows.append([next_txn_id(), a, b, round(base_amount * random.uniform(0.93, 1.07), 2), fmt(base_ts)])
        rows.append([next_txn_id(), b, c, round(base_amount * random.uniform(0.93, 1.07), 2), fmt(base_ts + timedelta(hours=random.uniform(1, 8)))])
        rows.append([next_txn_id(), c, a, round(base_amount * random.uniform(0.93, 1.07), 2), fmt(base_ts + timedelta(hours=random.uniform(9, 20)))])
    return rows

def generate_smurfing(num_patterns, used_accounts):
    rows = []
    available = [a for a in ACCOUNTS if a not in used_accounts]
    random.shuffle(available)
    idx = 0
    for _ in range(num_patterns):
        aggregator = available[idx]; idx += 1
        senders = [available[idx + j] for j in range(12)]; idx += 12
        receivers = [available[idx + j] for j in range(6)]; idx += 6
        used_accounts.add(aggregator)
        used_accounts.update(senders)
        used_accounts.update(receivers)
        base_ts = BASE_TIME + timedelta(days=random.randint(2, 20))
        base_amount = round(random.uniform(200, 600), 2)
        for s in senders:
            amt = round(base_amount * random.uniform(0.90, 1.10), 2)
            ts = base_ts + timedelta(hours=random.uniform(0, 23))
            rows.append([next_txn_id(), s, aggregator, amt, fmt(ts)])
        out_base = base_ts + timedelta(hours=24)
        for r in receivers:
            amt = round(base_amount * random.uniform(0.90, 1.10), 2)
            ts = out_base + timedelta(hours=random.uniform(0, 23))
            rows.append([next_txn_id(), aggregator, r, amt, fmt(ts)])
    return rows

def generate_payroll(num_patterns, used_accounts):
    rows = []
    available = [a for a in ACCOUNTS if a not in used_accounts]
    random.shuffle(available)
    idx = 0
    for _ in range(num_patterns):
        sender = available[idx]; idx += 1
        receivers = [available[idx + j] for j in range(15)]; idx += 15
        used_accounts.add(sender)
        used_accounts.update(receivers)
        base_ts = BASE_TIME + timedelta(days=random.randint(5, 25))
        base_amount = round(random.uniform(3000, 6000), 2)
        for r in receivers:
            amt = round(base_amount * random.uniform(0.97, 1.03), 2)
            ts = base_ts + timedelta(hours=random.uniform(0, 48))
            rows.append([next_txn_id(), sender, r, amt, fmt(ts)])
    return rows

def main():
    used = set()
    cycle_rows = generate_cycles(5, used)
    smurf_rows = generate_smurfing(2, used)
    payroll_rows = generate_payroll(2, used)
    injected = len(cycle_rows) + len(smurf_rows) + len(payroll_rows)
    normal_count = TOTAL_TRANSACTIONS - injected
    normal_rows = generate_normal(normal_count, used)
    all_rows = normal_rows + cycle_rows + smurf_rows + payroll_rows
    random.shuffle(all_rows)
    with open(OUTPUT_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transaction_id", "sender_id", "receiver_id", "amount", "timestamp"])
        w.writerows(all_rows)
    print(f"Generated {OUTPUT_FILE} with {len(all_rows)} transactions.")

if __name__ == "__main__":
    main()
