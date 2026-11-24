"""Jalankan dari host ketika proyek Compose aktif. Memakai pustaka standar Python."""
import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8088/api/"
SOURCE, TARGET = "2bJvI42r8EF3wxjOuDav4r", "4QNpBfC0zvjKqPJcyqBy9W"


def request(path, method="GET", data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = Request(BASE + path, method=method, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as res:
        raw = res.read()
        return json.loads(raw) if raw else None


def compose(*args):
    return subprocess.check_output(["docker", "compose", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT)


def stored_edges():
    query = f"MATCH (:User {{id:'pendengar-demo'}})-[r:LIKES]->(:Song {{id:'{SOURCE}'}}) RETURN count(r) AS edges"
    result = compose("exec", "-T", "neo4j", "sh", "-c",
                     'cypher-shell --format plain -u neo4j -p "${NEO4J_AUTH#*/}" "$1"', "sh", query)
    return int(result.strip().splitlines()[-1])


def stored_status():
    js = f"JSON.stringify(db.likes.findOne({{_id:'pendengar-demo/{SOURCE}'}}, {{_id:0,liked:1,pending:1,revision:1}}))"
    return json.loads(compose("exec", "-T", "mongo", "mongosh", "ruangnada", "--quiet", "--eval", js))


def wait_for(check, label, seconds=90):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if check():
                return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.4)
    raise AssertionError("Timeout: " + label)


def synced():
    s = request("status")
    return s["graph"] and s["pending"] == 0


def likes(song, flag):
    return request("songs/" + song + "/like", "PUT", {"liked": flag})


def ids(data):
    return [s["_id"] for s in data["songs"]]


def expect_error(code, path, method="GET", data=None):
    try:
        request(path, method, data)
    except HTTPError as err:
        assert err.code == code, (err.code, code)
    else:
        raise AssertionError("Respons seharusnya " + str(code))


def scenarios(outage):
    wait_for(synced, "kesiapan awal")
    initial = {s: request("songs/" + s)["liked"] for s in (SOURCE, TARGET)}
    playlist = None
    try:
        for s in initial:
            likes(s, False)
        wait_for(synced, "kondisi awal")
        assert SOURCE in ids(request("catalog?q=time"))
        assert SOURCE in ids(request("catalog?q=pitbull"))
        assert {SOURCE, TARGET}.issubset(set(ids(request("catalog?genre=Hip-Hop"))))
        assert request("songs/" + SOURCE)["song"]["genre"] == "Hip-Hop"
        related = request("songs/" + SOURCE + "/related")["songs"]
        assert any(s["_id"] == TARGET and "Pitbull" in s["reasons"] for s in related)
        print("LULUS TC-01: cari Time of Our Lives, temukan Give Me Everything melalui Pitbull.", flush=True)

        assert TARGET not in ids(request("recommendations"))
        with ThreadPoolExecutor(max_workers=6) as pool:
            updates = list(pool.map(lambda _: likes(SOURCE, True), range(10)))
        assert len({u["revision"] for u in updates}) == 1
        wait_for(synced, "sinkronisasi suka")
        assert stored_status()["liked"] and not stored_status()["pending"]
        assert stored_edges() == 1
        assert TARGET in ids(request("recommendations")) and SOURCE not in ids(request("recommendations"))
        likes(SOURCE, False)
        wait_for(synced, "sinkronisasi batal suka")
        assert stored_edges() == 0 and TARGET not in ids(request("recommendations"))
        print("LULUS TC-02: 10 PUT suka bersamaan, 1 relasi LIKES, rekomendasi berubah setelah batal suka.", flush=True)

        playlist = request("playlists", "POST", {"name": "Playlist uji integrasi"})
        path = "playlists/" + playlist["_id"]
        change = {"version": playlist["version"], "name": "Urutan uji", "songs": [TARGET, SOURCE]}
        playlist = request(path, "PUT", change)
        assert playlist["songs"] == [TARGET, SOURCE]
        expect_error(409, path, "PUT", change)
        expect_error(400, path, "PUT", dict(change, version=playlist["version"], songs=[SOURCE, SOURCE]))
        expect_error(400, "songs/" + SOURCE + "/like", "PUT", {"liked": "yes"})
        expect_error(404, "songs/tidak-ada")
        print("LULUS: urutan playlist, konflik versi, ID ganda, input suka, ID lagu.", flush=True)

        if outage:
            try:
                compose("stop", "neo4j")
                wait_for(lambda: not request("status")["graph"], "graf offline")
                likes(SOURCE, True)
                assert request("songs/" + SOURCE)["liked"]
                assert stored_status()["pending"]
                expect_error(503, "recommendations")
                compose("restart", "app")
                wait_for(lambda: request("songs/" + SOURCE)["pending"], "antrean bertahan setelah restart app")
                print("LULUS: MongoDB menyimpan suka saat Neo4j berhenti, antrean bertahan setelah restart aplikasi.", flush=True)
            finally:
                compose("start", "neo4j")
            wait_for(synced, "pemulihan Neo4j")
            assert stored_edges() == 1 and TARGET in ids(request("recommendations"))
            print("LULUS: Neo4j pulih, 1 LIKES terbentuk, 0 pembaruan tertunda.", flush=True)
    finally:
        if playlist:
            request("playlists/" + playlist["_id"], "DELETE", {"version": playlist["version"]})
        for song, liked in initial.items():
            likes(song, liked)
        wait_for(synced, "pemulihan kondisi demo")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pulihkan-graf", action="store_true",
                        help="Uji gangguan lokal dengan menghentikan dan menyalakan layanan Neo4j.")
    scenarios(parser.parse_args().pulihkan_graf)
