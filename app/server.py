import re
import threading
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from neo4j.exceptions import Neo4jError, DriverError
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError
from waitress import serve
from werkzeug.exceptions import HTTPException

from database import (CATALOG_FIELDS, USER, db, get_like, graph_rows, prepare_documents,
                      ready, save_like, sync_loop)
from queries import RECOMMEND, RELATED

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=32768, JSON_SORT_KEYS=False)


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@app.errorhandler(PyMongoError)
def mongo_error(error):
    app.logger.warning("MongoDB: %s", type(error).__name__)
    return jsonify(error="MongoDB belum dapat dihubungi. Coba lagi."), 503


@app.errorhandler(Neo4jError)
@app.errorhandler(DriverError)
def graph_error(error):
    app.logger.warning("Neo4j: %s", type(error).__name__)
    return jsonify(error="Neo4j belum tersedia. Pembaruan suka tetap disimpan di MongoDB."), 503


def require_graph():
    if not ready.is_set():
        abort(503, "Neo4j belum siap. Pembaruan suka tetap disimpan di MongoDB.")


def body():
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, "Kirim objek JSON.")
    return data


def field(data, key, limit, optional=False):
    value = data.get(key)
    if not isinstance(value, str) or (not optional and not value.strip()) or len(value.strip()) > limit:
        abort(400, f"Periksa isian {key} (maksimal {limit} karakter).")
    return value.strip()


def track(song):
    record = db.songs.find_one({"_id": song}, CATALOG_FIELDS)
    if not record:
        abort(404, "Lagu tidak ditemukan.")
    return record


def hydrate(rows):
    found = {s["_id"]: s for s in db.songs.find({"_id": {"$in": [r["id"] for r in rows]}}, CATALOG_FIELDS)}
    return [dict(found[r["id"]], reasons=sorted(r["reasons"]), score=r["score"]) for r in rows if r["id"] in found]


@app.get("/")
def index():
    return send_from_directory(Path(__file__).parent / "static", "index.html")


@app.get("/api/catalog")
def catalog():
    term = request.args.get("q", "").strip().casefold()
    genre = request.args.get("genre", "")
    if len(term) > 100 or len(genre) > 80:
        abort(400, "Pencarian terlalu panjang.")
    query = {}
    if term:
        query["keys"] = {"$regex": "^" + re.escape(term)}
    if genre:
        query["genre"] = genre
    songs = list(db.songs.find(query, CATALOG_FIELDS).sort("playlist_position", 1))
    return jsonify(songs=songs, genres=sorted(db.songs.distinct("genre")),
                   trace=["MongoDB · songs.find() berdasarkan judul, artis, atau genre"])


@app.get("/api/songs/<song>")
def detail(song):
    record = track(song)
    like = get_like(song) or {}
    return jsonify(song=record, liked=like.get("liked", False), pending=like.get("pending", False))


@app.get("/api/songs/<song>/related")
def related(song):
    track(song)
    require_graph()
    rows = graph_rows(RELATED, song=song)
    return jsonify(songs=hydrate(rows), trace=["MongoDB · baca lagu sumber",
                  "Neo4j · telusuri artis dan genre yang sama", "MongoDB · ambil detail kandidat berdasarkan ID"])


@app.put("/api/songs/<song>/like")
def like(song):
    track(song)
    liked = body().get("liked")
    if type(liked) is not bool:
        abort(400, "liked harus bernilai true atau false.")
    record = save_like(song, liked)
    return jsonify(liked=record["liked"], pending=record["pending"], revision=record["revision"],
                   trace=["MongoDB · simpan status suka dan penanda sinkronisasi dalam satu dokumen"])


@app.get("/api/recommendations")
def recommendations():
    require_graph()
    rows = graph_rows(RECOMMEND, user=USER)
    return jsonify(songs=hydrate(rows), trace=["Neo4j · telusuri LIKES, artis, dan genre",
                  "MongoDB · ambil metadata untuk kandidat yang belum disukai"])


@app.get("/api/likes")
def likes():
    ids = [r["song"] for r in db.likes.find({"user": USER, "liked": True})]
    return jsonify(songs=list(db.songs.find({"_id": {"$in": ids}}, CATALOG_FIELDS).sort("title", 1)))


@app.get("/api/status")
def status():
    pending = db.likes.count_documents({"pending": True})
    return jsonify(mongo=True, graph=ready.is_set(), pending=pending)


@app.route("/api/profile", methods=["GET", "PUT"])
def profile():
    if request.method == "PUT":
        data = body()
        db.users.update_one({"_id": USER}, {"$set": {"name": field(data, "name", 64),
                                                     "bio": field(data, "bio", 180, optional=True)}})
    return jsonify(db.users.find_one({"_id": USER}))


@app.route("/api/playlists", methods=["GET", "POST"])
def playlists():
    if request.method == "GET":
        return jsonify(playlists=list(db.playlists.find({"owner": USER}).sort("name", 1)))
    name = field(body(), "name", 64)
    record = {"_id": uuid.uuid4().hex, "owner": USER, "name": name, "songs": [], "version": 1}
    db.playlists.insert_one(record)
    return jsonify(record), 201


@app.route("/api/playlists/<pid>", methods=["PUT", "DELETE"])
def playlist(pid):
    data = body()
    version = data.get("version")
    if type(version) is not int or version < 1:
        abort(400, "Sertakan versi playlist yang dibaca.")
    key = {"_id": pid, "owner": USER, "version": version}
    if request.method == "DELETE":
        if db.playlists.delete_one(key).deleted_count:
            return "", 204
    else:
        name = field(data, "name", 64)
        ids = data.get("songs")
        if not isinstance(ids, list) or len(ids) > 200 or not all(isinstance(s, str) for s in ids):
            abort(400, "Daftar lagu tidak valid (maksimal 200).")
        if len(ids) != len(set(ids)) or db.songs.count_documents({"_id": {"$in": ids}}) != len(ids):
            abort(400, "Daftar memuat ID lagu ganda atau tidak dikenal.")
        changed = db.playlists.find_one_and_update(key, {"$set": {"name": name, "songs": ids},
                                                         "$inc": {"version": 1}},
                                                  return_document=ReturnDocument.AFTER)
        if changed:
            return jsonify(changed)
    if not db.playlists.find_one({"_id": pid, "owner": USER}, {"_id": 1}):
        abort(404, "Playlist tidak ditemukan.")
    abort(409, "Playlist telah berubah di tempat lain. Muat ulang dan ulangi perubahan.")


if __name__ == "__main__":
    prepare_documents()
    threading.Thread(target=sync_loop, name="proyeksi-suka", daemon=True).start()
    serve(app, host="0.0.0.0", port=8080, threads=8)
