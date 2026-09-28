#!/usr/bin/env python3
import argparse
import random
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def upload_a_file(fp: Path, cookie: str) -> str:
    api = "https://minute.dev.i.ai.gov.uk/api/proxy"
    sess = requests.Session()
    headers = {"Cookie": cookie}

    j = {"file_extension": fp.suffix.lstrip(".").lower()}
    rsp = sess.post(f"{api}/recordings", json=j, headers=headers, timeout=60)
    r = rsp.json()  # recording

    _data = fp.read_bytes()  # -> S3
    _headers = {"x-ms-blob-type": "BlockBlob"}
    rsp = sess.put(r["upload_url"], data=_data, headers=_headers, timeout=180)

    j = {"recording_id": r["id"], "template_name": "General"}  # start
    rsp = sess.post(f"{api}/transcriptions", json=j, headers=headers, timeout=60)

    transcription_id = rsp.json()["id"]
    for _ in range(1, 30 + 1):  # 5 mins
        _url = f"{api}/transcriptions/{transcription_id}"
        rsp = sess.get(url=_url, headers=headers, timeout=60)
        status = rsp.json().get("status")
        if status in ("completed", "failed"):
            return status
        time.sleep(10)

    return "unknown_error"


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario")
    parser.add_argument("--num", type=int)
    parser.add_argument("--cookie")
    args = parser.parse_args(argv)

    if args.scenario.lower().replace("_", "-") == "bbc-podcasting-house":
        _dir = Path(__file__).parent / ".downloads" / "bbc_podcasting_house"
        files = random.sample(list(_dir.glob("*.wav")), args.num)
    elif args.scenario.lower().replace("_", "") == "all-these-fancy-pens":
        # FROM=https://huggingface.co/datasets/edinburghcstr/ami
        fp = Path(__file__).parent / ".downloads" / "all_these_fancy_pens.wav"
        files = [fp for _ in range(args.num)]  # repeat _num_ times
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

    results = {}
    t0 = time.monotonic()
    print("Cooking...", end="", flush=True)  # noqa: T201
    with ThreadPoolExecutor(max_workers=len(files)) as executor:
        futures = {executor.submit(upload_a_file, file, args.cookie): file for file in files}
        for future in as_completed(futures):
            try:
                err_msg = None
                results[future] = future.result()
            except Exception as err:  # noqa: BLE001
                err_msg = str(err)
                results[future] = "unknown_error"
            counter = Counter(results.values())
            completed = counter["completed"]
            failed = counter["failed"]
            unknown_error = counter["unknown_error"]
            print(  # noqa: T201
                f"\r[{len(results):2d} / {len(files)}]"
                f" completed={completed:2d}"
                f" failed={failed:2d}"
                f" uknown_error={unknown_error:2d}"
                f" ({time.monotonic() - t0:.2f}s)",
                end="",
                flush=True,
            )
            if err_msg:
                print(f"          --- {err_msg}")  # noqa: T201
            time.sleep(0.5)  # seconds

    print("\n\n")  # noqa: T201


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
