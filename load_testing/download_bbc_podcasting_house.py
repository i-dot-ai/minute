#!/usr/bin/env python3
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

if __name__ == "__main__":
    print("--- BEGIN ---")  # noqa: T201

    url = "https://www.bbc.co.uk/programmes/p05ltqxn/episodes/downloads"
    headers = {"User-Agent": "Mozilla/5.0"}

    print("[ ] Finding...", end="", flush=True)  # noqa: T201
    req = urllib.request.Request(url, headers=headers)  # noqa: S310
    with urllib.request.urlopen(req) as rsp:  # noqa: S310
        charset = rsp.headers.get_content_charset()
        html = rsp.read().decode(charset)

    r = re.compile(
        r"//open\.live\.bbc\.co\.uk/mediaselector/6/redir/version/2\.0/"
        r"mediaset/audio-nondrm-download-low/proto/https/vpid/[a-z0-9]+\.mp3",
        re.IGNORECASE,
    )
    urls = {f"https:{_}" for _ in r.findall(html)}
    print("\r[x] Found        ")  # noqa: T201

    out_dir = Path(__file__).parent / ".downloads" / "bbc_podcasting_house"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[ ] Downloading...", end="", flush=True)  # noqa: T201
    for _url in urls:
        fn = _url.rsplit("/", 1)[-1]
        if not (dest := out_dir / fn).exists():
            req = urllib.request.Request(_url, headers=headers)  # noqa: S310
            with urllib.request.urlopen(req) as rsp, dest.open("wb") as f:  # noqa: S310
                f.write(rsp.read())
    print("\r[x] Downloaded        ")  # noqa: T201

    print("[ ] Converting...", end="", flush=True)  # noqa: T201
    if not (afconvert := shutil.which("afconvert")):
        msg = "afconvert not found"
        raise RuntimeError(msg)

    for mp3 in out_dir.glob("*.mp3"):
        if not (wav := mp3.with_suffix(".wav")).exists():
            subprocess.run(  # noqa: S603
                [
                    afconvert,
                    "-f",
                    "WAVE",
                    "-d",
                    "LEI16",
                    str(mp3),
                    str(wav),
                ],
                check=True,
            )
        mp3.unlink()  # remove
    print("\r[x] Converted        ")  # noqa: T201

    print("--- END ---")  # noqa: T201
