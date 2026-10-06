#!/usr/bin/env python3
import argparse
import random
import statistics
import sys
import time
import wave
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def check_response(response: requests.Response, step: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        msg = f"{step} failed ({response.status_code}): {response.text[:500]}"
        raise RuntimeError(msg) from error


def response_json(response: requests.Response, step: str, *required_fields: str) -> dict:
    check_response(response, step)
    try:
        data = response.json()
    except requests.JSONDecodeError as error:
        msg = f"{step} returned non-JSON ({response.status_code}): {response.text[:500]}"
        raise RuntimeError(msg) from error
    missing = [field for field in required_fields if field not in data]
    if missing:
        msg = f"{step} response missing {', '.join(missing)}: {data}"
        raise RuntimeError(msg)
    return data


def upload_a_file(fp: Path, cookie: str) -> dict:
    api = "https://minute.dev.i.ai.gov.uk/api/proxy"
    sess = requests.Session()
    headers = {"Cookie": cookie}

    with wave.open(str(fp), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        wav_duration = frames / rate

    start_time = time.time()

    t0 = time.monotonic()
    j = {"file_extension": fp.suffix.lstrip(".").lower()}
    rsp = sess.post(f"{api}/recordings", json=j, headers=headers, timeout=60)
    recording = response_json(rsp, "Create recording", "id", "upload_url")
    timeline = {"post_recordings": time.monotonic() - t0}

    t0 = time.monotonic()
    with fp.open("rb") as audio:
        rsp = sess.put(recording["upload_url"], data=audio, timeout=300)
    check_response(rsp, "Upload recording")
    timeline["upload_to_s3"] = time.monotonic() - t0

    t0 = time.monotonic()
    j = {"recording_id": recording["id"], "template_name": "General"}  # start
    rsp = sess.post(f"{api}/transcriptions", json=j, headers=headers, timeout=60)
    transcription = response_json(rsp, "Create transcription", "id")
    timeline["post_transcriptions"] = time.monotonic() - t0

    t0 = time.monotonic()
    status = "unknown_error"
    transcription_id = transcription["id"]
    for _ in range(1, 60 + 1):  # 10 mins
        _url = f"{api}/transcriptions/{transcription_id}"
        rsp = sess.get(url=_url, headers=headers, timeout=60)
        _status = response_json(rsp, "Get transcription", "status")["status"]
        if _status in ("completed", "failed"):
            status = _status
            break
        time.sleep(10)

    timeline["completed_or_failed"] = time.monotonic() - t0
    end_time = time.time()

    return {
        "fp": fp,
        "wav_duration": wav_duration,
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "duration": end_time - start_time,
        "timeline": timeline,
    }


def get_results(files: list[Path], cookie: str) -> list[dict]:
    results = {}
    t0 = time.monotonic()
    print("Cooking...", end="", flush=True)  # noqa: T201
    with ThreadPoolExecutor(max_workers=len(files)) as executor:
        futures = {executor.submit(upload_a_file, file, cookie): file for file in files}
        for future in as_completed(futures):
            try:
                err_msg = None
                results[future] = future.result()
            except Exception as err:  # noqa: BLE001
                err_msg = str(err)
                results[future] = {"status": "something_went_wrong"}

            counter = Counter([v["status"] for v in results.values()])
            completed = counter["completed"]
            failed = counter["failed"]
            unknown_error = counter["unknown_error"]
            something_went_wrong = counter["something_went_wrong"]
            print(  # noqa: T201
                f"\r[{len(results):2d} / {len(files)}]"
                f" completed={completed:2d}"
                f" failed={failed:2d}"
                f" uknown_error={unknown_error:2d}"
                f" something_went_wrong={something_went_wrong:2d}"
                f" ({time.monotonic() - t0:.2f}s)",
                end="",
                flush=True,
            )
            if err_msg:
                print(f"          --- {err_msg}")  # noqa: T201
            time.sleep(0.5)  # seconds

    return list(results.values())


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--n", "--num", type=int, required=True)
    parser.add_argument("--cookie", required=True)
    args = parser.parse_args(argv)

    scenario = args.scenario.lower().replace("_", "-")
    if scenario in {"bbc-podcasting-house", "bbc-broadcasting-house"}:
        _dir = Path(__file__).parent / ".downloads" / "bbc_podcasting_house"
        files = random.sample(list(_dir.glob("*.wav")), args.n)
    elif scenario == "all-these-fancy-pens":
        # FROM=https://huggingface.co/datasets/edinburghcstr/ami
        fp = Path(__file__).parent / ".downloads" / "all_these_fancy_pens.wav"
        files = [fp for _ in range(args.n)]  # repeat _num_ times
    else:
        msg = "Scenario not found"
        raise RuntimeError(msg)

    h1 = f"{args.scenario} ({len(files)})"
    print(f"\n+{'-' * (len(h1) + 2)}+")  # noqa: T201
    print(f"| {h1} |")  # noqa: T201
    print(f"+{'-' * (len(h1) + 2)}+")  # noqa: T201

    print(r"""

            (                 ,&&&.
             )                .,.&&
            (  (              \=__/
                )             ,'-'.
          (    (  ,,      _.__|/ /|
           ) /\ -((------((_|___/ |
         (  // | (`'      ((  `'--|
       _ -.;_/ \\--._      \\ \-._/.
      (_;-// | \ \-'.\    <_,\_\`--'|
      ( `.__ _  ___,')      <_,-'__,'
       `'(_ )_)(_)_)'
    """)  # noqa: T201

    url = "https://minute.dev.i.ai.gov.uk/transcriptions"
    print(f"Trace: \033]8;;{url}\033\\{url}\033]8;;\033\\\n")  # noqa: T201
    results = get_results(files, args.cookie)

    # --- metrics
    print("\n\n---\n")  # noqa: T201

    metrics = {
        "Wav (p10/90)": ("wav_duration", "range"),
        "Start time (delta)": ("start_time", "delta"),
        "End time (delta)": ("end_time", "delta"),
        "Duration (p10/90)": ("duration", "range"),
    }
    for label, (key, display) in metrics.items():
        data = [value for result in results if (value := result.get(key)) is not None]
        if not data:
            continue
        p10, p90 = (data[0], data[0]) if len(data) == 1 else statistics.quantiles(data, n=10, method="inclusive")[:9:8]
        value = f"[{p10:.2f}s, {p90:.2f}s]" if display == "range" else f"{p90 - p10:.2f}s"
        print(f"{label}: {value}")  # noqa: T201

    print()  # noqa: T201


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
