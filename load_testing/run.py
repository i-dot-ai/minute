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
    r = rsp.json()  # recording
    timeline = {"post_recordings": time.monotonic() - t0}

    t0 = time.monotonic()
    _data = fp.read_bytes()  # -> S3
    _headers = {"x-ms-blob-type": "BlockBlob"}
    with fp.open("rb") as _data:
        rsp = sess.put(r["upload_url"], data=_data, headers=_headers, timeout=300)
    timeline["upload_to_s3"] = time.monotonic() - t0

    t0 = time.monotonic()
    j = {"recording_id": r["id"], "template_name": "General"}  # start
    rsp = sess.post(f"{api}/transcriptions", json=j, headers=headers, timeout=60)
    timeline["post_transcriptions"] = time.monotonic() - t0

    t0 = time.monotonic()
    status = "unknown_error"
    transcription_id = rsp.json()["id"]
    for _ in range(1, 60 + 1):  # 10 mins
        _url = f"{api}/transcriptions/{transcription_id}"
        rsp = sess.get(url=_url, headers=headers, timeout=60)
        _status = rsp.json().get("status")
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
    parser.add_argument("--scenario")
    parser.add_argument("--n", type=int)
    parser.add_argument("--cookie")
    args = parser.parse_args(argv)

    if args.scenario.lower().replace("_", "-") == "bbc-podcasting-house":
        _dir = Path(__file__).parent / ".downloads" / "bbc_podcasting_house"
        files = random.sample(list(_dir.glob("*.wav")), args.n)
    elif args.scenario.lower().replace("_", "") == "all-these-fancy-pens":
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

    data = [_ for r in results if (_ := r.get("wav_duration"))]
    q = statistics.quantiles(data, n=10, method="inclusive")
    p10, p90 = q[0], q[8]  # low-res
    print(f"Wav (p10/90): [{p10:.2f}s, {p90:.2f}s]")  # noqa: T201

    data = [_ for r in results if (_ := r.get("start_time"))]
    q = statistics.quantiles(data, n=10, method="inclusive")
    p10, p90 = q[0], q[8]  # low-res
    print(f"Start time (delta): {p90 - p10:.2f}s")  # noqa: T201

    data = [_ for r in results if (_ := r.get("end_time"))]
    q = statistics.quantiles(data, n=10, method="inclusive")
    p10, p90 = q[0], q[8]  # low-res
    print(f"End time (delta): {p90 - p10:.2f}s")  # noqa: T201

    data = [_ for r in results if (_ := r.get("duration"))]
    q = statistics.quantiles(data, n=10, method="inclusive")
    p10, p90 = q[0], q[8]  # low-res
    print(f"Duration (p10/90): [{p10:.2f}s, {p90:.2f}s]")  # noqa: T201

    print()  # noqa: T201


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
