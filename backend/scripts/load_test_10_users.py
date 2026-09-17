"""Load test thực tế: 10 người dùng hỏi đồng thời 2 câu liên tiếp."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx


QUESTION_1 = "Trả lời đúng một câu ngắn: 2 + 2 bằng bao nhiêu?"
QUESTION_2 = "Dựa trên câu trước, trả lời đúng một câu ngắn: 3 + 3 bằng bao nhiêu?"
TEST_PASSWORD = "LoadTest@2k3!"


@dataclass
class TestUser:
    number: int
    email: str
    token: str
    conversation_id: str


@dataclass
class Result:
    user: int
    request_id: str
    status: str
    submit_ms: float
    queue_s: float | None
    first_token_s: float | None
    complete_s: float
    retry_count: int
    attempt_count: int | None
    error: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--run-id",
        default=datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6],
    )
    return parser.parse_args()


def request_error(response: httpx.Response) -> RuntimeError:
    try:
        detail = response.json().get("detail", response.text)
    except (ValueError, AttributeError):
        detail = response.text
    return RuntimeError(f"HTTP {response.status_code}: {detail}")


async def provision_user(
    client: httpx.AsyncClient, base_url: str, run_id: str, number: int
) -> TestUser:
    email = f"load10-{run_id}-u{number:02d}@example.com"
    response = await client.post(
        f"{base_url}/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    if response.status_code != 201:
        raise request_error(response)
    token = response.json()["access_token"]

    response = await client.post(
        f"{base_url}/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": f"Load test {run_id} - U{number:02d}"},
    )
    if response.status_code != 201:
        raise request_error(response)

    return TestUser(number, email, token, response.json()["id"])


async def read_generation_events(
    client: httpx.AsyncClient,
    base_url: str,
    test_user: TestUser,
    request_id: str,
    started_at: float,
    accepted_at: float,
) -> tuple[str, float | None, float | None, float, int, str | None]:
    headers = {
        "Authorization": f"Bearer {test_user.token}",
        "Accept": "text/event-stream",
    }
    generating_at: float | None = None
    first_delta_at: float | None = None
    retry_count = 0
    status = "UNKNOWN"
    error: str | None = None
    event_name = ""
    data_lines: list[str] = []

    async with client.stream(
        "GET",
        f"{base_url}/generations/{request_id}/events",
        headers=headers,
    ) as response:
        if response.status_code != 200:
            await response.aread()
            raise request_error(response)

        async for line in response.aiter_lines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
                continue
            if line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
                continue
            if line != "" or not event_name:
                continue

            now = time.perf_counter()
            raw_data = "\n".join(data_lines)
            try:
                payload = json.loads(raw_data) if raw_data else {}
            except json.JSONDecodeError:
                payload = {}

            if event_name == "generating" and generating_at is None:
                generating_at = now
            elif event_name == "delta" and first_delta_at is None:
                first_delta_at = now
            elif event_name == "retrying":
                retry_count += 1
            elif event_name in {"completed", "failed"}:
                status = "DONE" if event_name == "completed" else "FAILED"
                error = payload.get("message") or payload.get("error")
                return (
                    status,
                    None if generating_at is None else generating_at - accepted_at,
                    None if first_delta_at is None else first_delta_at - started_at,
                    now - started_at,
                    retry_count,
                    error,
                )

            event_name = ""
            data_lines = []

    raise RuntimeError(f"Luồng sự kiện của request {request_id} kết thúc bất thường")


async def ask(
    client: httpx.AsyncClient,
    base_url: str,
    test_user: TestUser,
    question: str,
    start_signal: asyncio.Event,
    wave: str,
) -> Result:
    # Mọi coroutine cùng chờ một tín hiệu để thời điểm gửi gần như đồng thời.
    await start_signal.wait()
    started_at = time.perf_counter()
    response = await client.post(
        f"{base_url}/generations",
        headers={"Authorization": f"Bearer {test_user.token}"},
        json={
            "conversation_id": test_user.conversation_id,
            "message": question,
            "client_request_id": str(uuid.uuid4()),
            "model": "default",
        },
    )
    accepted_at = time.perf_counter()
    if response.status_code != 202:
        raise request_error(response)

    request_id = response.json()["request_id"]
    status, queue_s, first_token_s, complete_s, retries, error = (
        await read_generation_events(
            client, base_url, test_user, request_id, started_at, accepted_at
        )
    )

    detail = await client.get(
        f"{base_url}/generations/{request_id}",
        headers={"Authorization": f"Bearer {test_user.token}"},
    )
    attempt_count = detail.json().get("attempt_count") if detail.status_code == 200 else None
    print(
        f"[{wave}] U{test_user.number:02d} {status}: "
        f"token đầu={format_seconds(first_token_s)}, xong={complete_s:.2f}s, "
        f"retry={retries}",
        flush=True,
    )
    return Result(
        user=test_user.number,
        request_id=request_id,
        status=status,
        submit_ms=(accepted_at - started_at) * 1000,
        queue_s=queue_s,
        first_token_s=first_token_s,
        complete_s=complete_s,
        retry_count=retries,
        attempt_count=attempt_count,
        error=error,
    )


async def run_wave(
    client: httpx.AsyncClient,
    base_url: str,
    users: list[TestUser],
    question: str,
    wave: str,
) -> list[Result]:
    signal = asyncio.Event()
    tasks = [
        asyncio.create_task(ask(client, base_url, user, question, signal, wave))
        for user in users
    ]
    await asyncio.sleep(0)
    signal.set()
    results = await asyncio.gather(*tasks)
    return sorted(results, key=lambda item: item.user)


def format_seconds(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}s"


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percent * len(ordered)) - 1)]


def print_results(title: str, results: list[Result]) -> None:
    print(f"\n## {title}")
    print("| User | Nhận job | Chờ queue | Token đầu | Hoàn tất | Retry | Attempt | Trạng thái |")
    print("|---:|---:|---:|---:|---:|---:|---:|:---|")
    for result in results:
        print(
            f"| U{result.user:02d} | {result.submit_ms:.0f}ms | "
            f"{format_seconds(result.queue_s)} | {format_seconds(result.first_token_s)} | "
            f"{result.complete_s:.2f}s | {result.retry_count} | "
            f"{result.attempt_count if result.attempt_count is not None else '-'} | "
            f"{result.status} |"
        )

    first_tokens = [item.first_token_s for item in results if item.first_token_s is not None]
    completes = [item.complete_s for item in results]
    if first_tokens:
        print(
            "Token đầu (min / trung bình / p95 / max): "
            f"{min(first_tokens):.2f}s / {statistics.mean(first_tokens):.2f}s / "
            f"{percentile(first_tokens, 0.95):.2f}s / {max(first_tokens):.2f}s"
        )
    print(
        "Hoàn tất (min / trung bình / p95 / max): "
        f"{min(completes):.2f}s / {statistics.mean(completes):.2f}s / "
        f"{percentile(completes, 0.95):.2f}s / {max(completes):.2f}s"
    )


async def main() -> int:
    args = parse_args()
    if args.users < 1:
        raise ValueError("--users phải lớn hơn 0")

    timeout = httpx.Timeout(connect=10, read=None, write=30, pool=30)
    limits = httpx.Limits(max_connections=max(30, args.users * 3))
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        health = await client.get(f"{args.base_url}/health")
        if health.status_code != 200:
            raise request_error(health)

        print(f"RUN_ID={args.run_id}")
        print(f"Đang tạo {args.users} tài khoản và hội thoại test...")
        users = await asyncio.gather(
            *[
                provision_user(client, args.base_url, args.run_id, number)
                for number in range(1, args.users + 1)
            ]
        )

        async with asyncio.timeout(args.timeout):
            print("\nBắt đầu câu 1 đồng thời...")
            first = await run_wave(client, args.base_url, list(users), QUESTION_1, "Q1")
            print_results("Câu 1", first)
            if any(item.status != "DONE" for item in first):
                print("Không chạy câu 2 vì có người chưa hoàn tất câu 1.")
                return 2

            print("\nBắt đầu câu 2 đồng thời ngay sau khi cả 10 người xong câu 1...")
            second = await run_wave(client, args.base_url, list(users), QUESTION_2, "Q2")
            print_results("Câu 2", second)

    failures = sum(item.status != "DONE" for item in first + second)
    print(f"\nKết thúc: {len(first) + len(second) - failures}/20 request thành công.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
