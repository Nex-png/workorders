import time
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed

from workorders.db import get_connection, init_db, add_work_order, list_work_orders, close_work_order

def rand_issue(n=20):
    return "".join(random.choice(string.ascii_letters + " ") for _ in range(n)).strip()

def worker(db_path: str, ops: int):
    conn = get_connection(db_path)
    init_db(conn)

    ids = []
    for _ in range(ops):
        # 70% add, 20% list, 10% close (if any)
        r = random.random()
        if r < 0.7:
            wid = add_work_order(conn, "KMT-102", rand_issue(35), random.choice(["low","med","high"]))
            ids.append(wid)
        elif r < 0.9:
            _ = list_work_orders(conn)
        else:
            if ids:
                close_work_order(conn, random.choice(ids))

    conn.close()
    return ops

def main():
    db_path = "workorders.db"
    threads = 8
    ops_per_thread = 200

    start = time.time()
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = [ex.submit(worker, db_path, ops_per_thread) for _ in range(threads)]
        for f in as_completed(futs):
            f.result()

    elapsed = time.time() - start
    total_ops = threads * ops_per_thread
    print(f"Total ops: {total_ops} in {elapsed:.2f}s -> {total_ops/elapsed:.1f} ops/sec")

if __name__ == "__main__":
    main()
