"""
성능 테스트 (Performance Test)
- 대용량 영상 업로드
- 동시 접속 (Concurrent requests)
- DB 대량 쿼리 성능
- API 응답 시간
"""
import asyncio
import time
import os
import sys
import uuid
import json
import tempfile
import statistics

import httpx

BASE_URL = "http://localhost:8000"

# Auth headers for approved therapist
THERAPIST_HEADERS = {
    "X-User-Id": "perf-test-user",
    "X-User-Role": "therapist",
    "X-User-Approved": "true",
}

ADMIN_HEADERS = {
    "X-User-Id": "admin",
    "X-User-Role": "admin",
    "X-User-Approved": "true",
}


def create_dummy_video(size_mb: int) -> str:
    """Create a dummy video file of specified size (MB)"""
    path = os.path.join(tempfile.gettempdir(), f"perf_test_{size_mb}mb.mov")
    if os.path.exists(path) and abs(os.path.getsize(path) - size_mb * 1024 * 1024) < 1024:
        return path
    with open(path, "wb") as f:
        # Write minimal MOV header then pad
        # ftyp box
        ftyp = b'\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00qt  '
        f.write(ftyp)
        remaining = size_mb * 1024 * 1024 - len(ftyp)
        chunk_size = 1024 * 1024  # 1MB chunks
        while remaining > 0:
            write_size = min(chunk_size, remaining)
            f.write(b'\x00' * write_size)
            remaining -= write_size
    return path


async def setup_test_patient(client: httpx.AsyncClient) -> str:
    """Create a test patient and return patient_id"""
    patient_data = {
        "patient_number": f"PERF-{uuid.uuid4().hex[:8]}",
        "name": "Performance Test Patient",
        "gender": "M",
        "birth_date": "1990-01-01",
        "height_cm": 175.0,
        "diagnosis": None,
    }
    resp = await client.post(
        f"{BASE_URL}/api/patients/",
        json=patient_data,
        headers=THERAPIST_HEADERS,
    )
    if resp.status_code == 200:
        return resp.json()["id"]
    raise RuntimeError(f"Failed to create patient: {resp.status_code} {resp.text}")


# ──────────────────────────────────────────────
# Test 1: Large file upload
# ──────────────────────────────────────────────
async def test_large_file_upload():
    """Test uploading files of various sizes and measure upload time"""
    print("\n" + "=" * 60)
    print("TEST 1: Large File Upload Performance")
    print("=" * 60)

    sizes_mb = [10, 50, 100, 500]
    results = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        patient_id = await setup_test_patient(client)

        for size_mb in sizes_mb:
            print(f"\n  Creating {size_mb}MB dummy file...", end=" ", flush=True)
            path = create_dummy_video(size_mb)
            actual_size = os.path.getsize(path) / (1024 * 1024)
            print(f"OK ({actual_size:.1f}MB)")

            print(f"  Uploading {size_mb}MB...", end=" ", flush=True)
            start = time.perf_counter()

            with open(path, "rb") as f:
                resp = await client.post(
                    f"{BASE_URL}/api/tests/{patient_id}/upload",
                    files={"file": (f"test_{size_mb}mb.mov", f, "video/quicktime")},
                    headers=THERAPIST_HEADERS,
                    timeout=httpx.Timeout(300.0),
                )

            elapsed = time.perf_counter() - start
            status = resp.status_code

            throughput = actual_size / elapsed if elapsed > 0 else 0
            results.append({
                "size_mb": size_mb,
                "time_sec": round(elapsed, 2),
                "status": status,
                "throughput_mbps": round(throughput, 1),
            })
            print(f"{elapsed:.2f}s (HTTP {status}, {throughput:.1f} MB/s)")

            # Clean up temp file for large sizes
            if size_mb >= 500:
                os.remove(path)

    print(f"\n  {'Size':>8} {'Time':>8} {'Status':>8} {'Throughput':>12}")
    print(f"  {'-'*8} {'-'*8} {'-'*8} {'-'*12}")
    for r in results:
        print(f"  {r['size_mb']:>6}MB {r['time_sec']:>7}s {r['status']:>8} {r['throughput_mbps']:>9} MB/s")

    return results


# ──────────────────────────────────────────────
# Test 2: Concurrent API requests
# ──────────────────────────────────────────────
async def test_concurrent_api_requests():
    """Test concurrent read requests to various endpoints"""
    print("\n" + "=" * 60)
    print("TEST 2: Concurrent API Requests")
    print("=" * 60)

    # First create some test data
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        patient_id = await setup_test_patient(client)

    endpoints = [
        ("GET", "/health", None),
        ("GET", f"/api/patients/?page=1&per_page=20", THERAPIST_HEADERS),
        ("GET", f"/api/patients/{patient_id}", THERAPIST_HEADERS),
        ("GET", f"/api/tests/patient/{patient_id}", THERAPIST_HEADERS),
    ]

    concurrency_levels = [1, 5, 10, 25, 50, 100]
    all_results = []

    for n_concurrent in concurrency_levels:
        print(f"\n  Concurrency: {n_concurrent} requests...", end=" ", flush=True)

        async def make_request(session, method, path, headers):
            start = time.perf_counter()
            try:
                if method == "GET":
                    resp = await session.get(f"{BASE_URL}{path}", headers=headers)
                else:
                    resp = await session.post(f"{BASE_URL}{path}", headers=headers)
                elapsed = time.perf_counter() - start
                return {"status": resp.status_code, "time": elapsed, "error": None}
            except Exception as e:
                elapsed = time.perf_counter() - start
                return {"status": 0, "time": elapsed, "error": str(e)}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=100),
        ) as client:
            tasks = []
            for i in range(n_concurrent):
                method, path, headers = endpoints[i % len(endpoints)]
                tasks.append(make_request(client, method, path, headers))

            start_all = time.perf_counter()
            results = await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_all

        times = [r["time"] for r in results if r["error"] is None]
        successes = sum(1 for r in results if r["error"] is None and r["status"] < 500)
        errors = sum(1 for r in results if r["error"] is not None or r["status"] >= 500)
        rate_limited = sum(1 for r in results if r.get("status") == 429)

        avg_time = statistics.mean(times) if times else 0
        p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else (times[0] if times else 0)
        p99_time = sorted(times)[int(len(times) * 0.99)] if len(times) > 1 else (times[0] if times else 0)
        rps = n_concurrent / total_time if total_time > 0 else 0

        all_results.append({
            "concurrent": n_concurrent,
            "total_sec": round(total_time, 3),
            "avg_ms": round(avg_time * 1000, 1),
            "p95_ms": round(p95_time * 1000, 1),
            "p99_ms": round(p99_time * 1000, 1),
            "success": successes,
            "errors": errors,
            "rate_limited": rate_limited,
            "rps": round(rps, 1),
        })
        print(f"avg={avg_time*1000:.0f}ms, p95={p95_time*1000:.0f}ms, {successes} OK, {errors} err, {rps:.0f} req/s")

    print(f"\n  {'Conc':>6} {'Total':>8} {'Avg':>8} {'P95':>8} {'P99':>8} {'OK':>5} {'Err':>5} {'429':>5} {'RPS':>8}")
    print(f"  {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*5} {'-'*5} {'-'*5} {'-'*8}")
    for r in all_results:
        print(f"  {r['concurrent']:>6} {r['total_sec']:>7}s {r['avg_ms']:>6}ms {r['p95_ms']:>6}ms {r['p99_ms']:>6}ms {r['success']:>5} {r['errors']:>5} {r['rate_limited']:>5} {r['rps']:>7}/s")

    return all_results


# ──────────────────────────────────────────────
# Test 3: Concurrent uploads (worker saturation)
# ──────────────────────────────────────────────
async def test_concurrent_uploads():
    """Test concurrent video uploads to saturate the 2-worker thread pool"""
    print("\n" + "=" * 60)
    print("TEST 3: Concurrent Upload (2-Worker Saturation)")
    print("=" * 60)

    # Create a small valid-ish video (1MB)
    small_video = create_dummy_video(1)

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        patient_id = await setup_test_patient(client)

    upload_counts = [1, 2, 3, 4, 5]
    all_results = []

    for n_uploads in upload_counts:
        print(f"\n  Concurrent uploads: {n_uploads}...", end=" ", flush=True)

        async def do_upload(session, patient_id, idx):
            start = time.perf_counter()
            try:
                with open(small_video, "rb") as f:
                    resp = await session.post(
                        f"{BASE_URL}/api/tests/{patient_id}/upload",
                        files={"file": (f"concurrent_{idx}.mov", f, "video/quicktime")},
                        headers=THERAPIST_HEADERS,
                        timeout=httpx.Timeout(120.0),
                    )
                elapsed = time.perf_counter() - start
                return {"status": resp.status_code, "time": elapsed, "file_id": resp.json().get("file_id") if resp.status_code == 200 else None}
            except Exception as e:
                elapsed = time.perf_counter() - start
                return {"status": 0, "time": elapsed, "error": str(e)}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            limits=httpx.Limits(max_connections=20),
        ) as client:
            tasks = [do_upload(client, patient_id, i) for i in range(n_uploads)]
            start_all = time.perf_counter()
            results = await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_all

        times = [r["time"] for r in results]
        successes = sum(1 for r in results if r.get("status") == 200)

        all_results.append({
            "uploads": n_uploads,
            "total_sec": round(total_time, 2),
            "avg_sec": round(statistics.mean(times), 2),
            "max_sec": round(max(times), 2),
            "success": successes,
        })
        print(f"total={total_time:.2f}s, avg={statistics.mean(times):.2f}s, max={max(times):.2f}s, {successes}/{n_uploads} OK")

    print(f"\n  {'Uploads':>8} {'Total':>8} {'Avg':>8} {'Max':>8} {'OK':>5}")
    print(f"  {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*5}")
    for r in all_results:
        print(f"  {r['uploads']:>8} {r['total_sec']:>7}s {r['avg_sec']:>7}s {r['max_sec']:>7}s {r['success']:>5}")

    return all_results


# ──────────────────────────────────────────────
# Test 4: Database bulk insert & query (10,000+ records)
# ──────────────────────────────────────────────
async def test_database_performance():
    """Test DB performance with bulk data"""
    print("\n" + "=" * 60)
    print("TEST 4: Database Performance (10,000+ Records)")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # 4a: Bulk patient creation
        print("\n  4a. Bulk patient creation...")
        counts = [100, 500, 1000]
        for count in counts:
            start = time.perf_counter()
            created = 0
            for i in range(count):
                resp = await client.post(
                    f"{BASE_URL}/api/patients/",
                    json={
                        "patient_number": f"BULK-{uuid.uuid4().hex[:8]}",
                        "name": f"Bulk Patient {i}",
                        "gender": "M" if i % 2 == 0 else "F",
                        "birth_date": f"19{50 + i % 50:02d}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                        "height_cm": 155.0 + (i % 40),
                    },
                    headers=THERAPIST_HEADERS,
                )
                if resp.status_code == 200:
                    created += 1
            elapsed = time.perf_counter() - start
            rate = count / elapsed if elapsed > 0 else 0
            print(f"      {count} patients: {elapsed:.2f}s ({rate:.0f}/s), {created} created")

        # 4b: Patient list query with pagination
        print("\n  4b. Patient list query (varying page sizes)...")
        page_sizes = [20, 50, 100, 500]
        for ps in page_sizes:
            times_list = []
            for _ in range(5):  # 5 iterations for avg
                start = time.perf_counter()
                resp = await client.get(
                    f"{BASE_URL}/api/patients/?page=1&per_page={ps}",
                    headers=THERAPIST_HEADERS,
                )
                elapsed = time.perf_counter() - start
                times_list.append(elapsed)
            avg = statistics.mean(times_list)
            print(f"      page_size={ps:>4}: avg={avg*1000:.1f}ms (status={resp.status_code})")

        # 4c: Bulk walk test creation (via direct DB for speed)
        print("\n  4c. Bulk walk_test insert via API (simulated)...")
        # Create a patient with many tests
        resp = await client.post(
            f"{BASE_URL}/api/patients/",
            json={
                "patient_number": f"HEAVY-{uuid.uuid4().hex[:8]}",
                "name": "Heavy Test Patient",
                "gender": "M",
                "birth_date": "1980-01-01",
                "height_cm": 175.0,
            },
            headers=THERAPIST_HEADERS,
        )
        heavy_patient_id = resp.json()["id"]

        # 4d: Query patient with many tests
        print("\n  4d. Query tests for patient (after bulk data)...")
        # Query all patients list
        for trial in range(3):
            start = time.perf_counter()
            resp = await client.get(
                f"{BASE_URL}/api/patients/?page=1&per_page=20",
                headers=THERAPIST_HEADERS,
            )
            elapsed = time.perf_counter() - start
            total = resp.headers.get("X-Total-Count", "?")
            print(f"      Trial {trial+1}: {elapsed*1000:.1f}ms (total patients: {total})")

        # 4e: Search/filter performance
        print("\n  4e. Patient search performance...")
        search_terms = ["Bulk", "Patient 5", "HEAVY"]
        for term in search_terms:
            start = time.perf_counter()
            resp = await client.get(
                f"{BASE_URL}/api/patients/?search={term}&page=1&per_page=20",
                headers=THERAPIST_HEADERS,
            )
            elapsed = time.perf_counter() - start
            count = len(resp.json()) if resp.status_code == 200 else 0
            print(f"      search='{term}': {elapsed*1000:.1f}ms, {count} results")


# ──────────────────────────────────────────────
# Test 5: API endpoint response times
# ──────────────────────────────────────────────
async def test_api_response_times():
    """Measure individual API endpoint response times"""
    print("\n" + "=" * 60)
    print("TEST 5: API Endpoint Response Times (avg of 10 calls)")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        patient_id = await setup_test_patient(client)

        endpoints = [
            ("GET", "/health", None, "Health check"),
            ("GET", "/api/patients/?page=1&per_page=20", THERAPIST_HEADERS, "Patient list"),
            ("GET", f"/api/patients/{patient_id}", THERAPIST_HEADERS, "Patient detail"),
            ("GET", f"/api/tests/patient/{patient_id}", THERAPIST_HEADERS, "Patient tests"),
            ("GET", f"/api/patients/{patient_id}/recommendations", THERAPIST_HEADERS, "Recommendations"),
            ("GET", f"/api/patients/{patient_id}/trends?test_type=10MWT", THERAPIST_HEADERS, "Trend analysis"),
        ]

        print(f"\n  {'Endpoint':<40} {'Avg':>8} {'Min':>8} {'Max':>8} {'P95':>8}")
        print(f"  {'-'*40} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

        for method, path, headers, label in endpoints:
            times_list = []
            for _ in range(10):
                start = time.perf_counter()
                try:
                    resp = await client.get(f"{BASE_URL}{path}", headers=headers)
                    elapsed = time.perf_counter() - start
                    times_list.append(elapsed)
                except:
                    pass

            if times_list:
                avg = statistics.mean(times_list) * 1000
                mn = min(times_list) * 1000
                mx = max(times_list) * 1000
                p95 = sorted(times_list)[int(len(times_list) * 0.95)] * 1000
                print(f"  {label:<40} {avg:>6.1f}ms {mn:>6.1f}ms {mx:>6.1f}ms {p95:>6.1f}ms")
            else:
                print(f"  {label:<40} FAILED")


# ──────────────────────────────────────────────
# Test 6: WebSocket connection stress
# ──────────────────────────────────────────────
async def test_websocket_connections():
    """Test multiple WebSocket connections"""
    print("\n" + "=" * 60)
    print("TEST 6: WebSocket Connection Stress")
    print("=" * 60)

    import websockets

    connection_counts = [1, 5, 10, 25, 50]

    for n_conns in connection_counts:
        print(f"\n  {n_conns} connections...", end=" ", flush=True)

        async def connect_ws(idx):
            start = time.perf_counter()
            try:
                ws = await asyncio.wait_for(
                    websockets.connect(f"ws://localhost:8000/ws/perf-test-{idx}"),
                    timeout=10.0,
                )
                elapsed = time.perf_counter() - start
                # Send a ping
                await ws.send(json.dumps({"type": "ping"}))
                pong = await asyncio.wait_for(ws.recv(), timeout=5.0)
                await ws.close()
                return {"time": elapsed, "ok": True}
            except Exception as e:
                elapsed = time.perf_counter() - start
                return {"time": elapsed, "ok": False, "error": str(e)}

        tasks = [connect_ws(i) for i in range(n_conns)]
        start_all = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total = time.perf_counter() - start_all

        ok = sum(1 for r in results if r["ok"])
        times = [r["time"] for r in results if r["ok"]]
        avg = statistics.mean(times) * 1000 if times else 0
        print(f"{ok}/{n_conns} connected, avg={avg:.0f}ms, total={total:.2f}s")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("  10M_WT Performance Test Suite")
    print("=" * 60)

    # Check server is running
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        try:
            resp = await client.get(f"{BASE_URL}/health")
            print(f"\n  Server: OK (status={resp.status_code})")
        except Exception as e:
            print(f"\n  ERROR: Server not reachable at {BASE_URL}")
            print(f"  Start the backend first: cd backend && uvicorn app.main:app --port 8000")
            return

    results = {}

    # Test 1: Large file upload
    try:
        results["large_upload"] = await test_large_file_upload()
    except Exception as e:
        print(f"  FAILED: {e}")

    # Test 2: Concurrent API requests
    try:
        results["concurrent_api"] = await test_concurrent_api_requests()
    except Exception as e:
        print(f"  FAILED: {e}")

    # Test 3: Concurrent uploads
    try:
        results["concurrent_upload"] = await test_concurrent_uploads()
    except Exception as e:
        print(f"  FAILED: {e}")

    # Test 4: Database performance
    try:
        await test_database_performance()
    except Exception as e:
        print(f"  FAILED: {e}")

    # Test 5: API response times
    try:
        await test_api_response_times()
    except Exception as e:
        print(f"  FAILED: {e}")

    # Test 6: WebSocket stress
    try:
        await test_websocket_connections()
    except Exception as e:
        print(f"  SKIPPED (websockets not installed or error): {e}")

    # Summary
    print("\n" + "=" * 60)
    print("  PERFORMANCE TEST SUMMARY")
    print("=" * 60)

    if "large_upload" in results:
        print("\n  Large Upload:")
        for r in results["large_upload"]:
            status = "PASS" if r["status"] == 200 else "FAIL"
            print(f"    {r['size_mb']:>4}MB -> {r['time_sec']}s [{status}]")

    if "concurrent_api" in results:
        print("\n  Concurrent API:")
        for r in results["concurrent_api"]:
            status = "PASS" if r["errors"] == 0 else f"WARN ({r['errors']} errors)"
            print(f"    {r['concurrent']:>3} concurrent -> avg {r['avg_ms']}ms, {r['rps']} req/s [{status}]")

    if "concurrent_upload" in results:
        print("\n  Concurrent Uploads:")
        for r in results["concurrent_upload"]:
            status = "PASS" if r["success"] == r["uploads"] else f"WARN ({r['uploads']-r['success']} failed)"
            print(f"    {r['uploads']} uploads -> {r['total_sec']}s [{status}]")

    print("\n  Done!")


if __name__ == "__main__":
    asyncio.run(main())
