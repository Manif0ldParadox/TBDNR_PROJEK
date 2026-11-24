import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from neo4j import GraphDatabase
from pymongo import MongoClient, ReturnDocument
from pymongo.write_concern import WriteConcern

from audio_samples import DURATION
from queries import CATALOG_GRAPH, CLEAR_LIKE, SET_LIKE

USER = "pendengar-demo"
mongo = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=2500, tz_aware=True)
db = mongo.get_database("ruangnada", write_concern=WriteConcern(w=1, j=True))
graph = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=("neo4j", os.environ["NEO4J_PASSWORD"]),
                             connection_timeout=2, connection_acquisition_timeout=3,
                             max_transaction_retry_time=1)
ready = threading.Event()
wake = threading.Event()
CATALOG_FIELDS = {"keys": 0}


def utcnow():
    return datetime.now(timezone.utc)


def prepare_documents():
    tracks = json.loads(Path(__file__).with_name("catalog.json").read_text())
    current_ids = [track["_id"] for track in tracks]
    current_set = set(current_ids)
    for playlist in db.playlists.find({}, {"songs": 1, "version": 1}):
        songs = [song for song in playlist.get("songs", []) if song in current_set]
        if songs != playlist.get("songs", []):
            db.playlists.update_one({"_id": playlist["_id"]},
                                    {"$set": {"songs": songs}, "$inc": {"version": 1}})
    db.likes.delete_many({"song": {"$nin": current_ids}})
    db.songs.delete_many({"_id": {"$nin": current_ids}})
    for track in tracks:
        song = {k: v for k, v in track.items() if k not in ("root", "bpm")}
        phrases = [song[field].casefold() for field in ("title", "artist", "album", "genre")]
        song.update(seconds=DURATION, audio="/static/audio/" + song["_id"] + ".wav",
                    keys=sorted(set(phrases + [w for phrase in phrases for w in phrase.split()])))
        db.songs.replace_one({"_id": song["_id"]}, song, upsert=True)
    db.songs.create_index("keys")
    db.songs.create_index("genre")
    db.songs.create_index("playlist_position")
    db.playlists.create_index([("owner", 1), ("name", 1)])
    db.likes.create_index([("pending", 1), ("changed_at", 1)])
    db.likes.create_index([("user", 1), ("liked", 1)])
    db.users.update_one({"_id": USER}, {"$setOnInsert": {"name": "Pendengar Demo", "bio": ""}}, upsert=True)


def get_like(song):
    return db.likes.find_one({"_id": USER + "/" + song})


def save_like(song, liked):
    # Desired state and durable delivery flag share one atomic document write.
    key = USER + "/" + song
    changed = {"$ne": [{"$ifNull": ["$liked", None]}, liked]}
    result = db.likes.find_one_and_update({"_id": key}, [{"$set": {
        "user": USER, "song": song, "liked": liked,
        "pending": {"$cond": [changed, True, "$pending"]},
        "revision": {"$add": [{"$ifNull": ["$revision", 0]}, {"$cond": [changed, 1, 0]}]},
        "changed_at": {"$cond": [changed, "$$NOW", "$changed_at"]},
    }}], upsert=True, return_document=ReturnDocument.AFTER)
    wake.set()
    return result


def graph_rows(query, **params):
    with graph.session(database="neo4j") as session:
        return session.run(query, **params).data()


def prepare_graph():
    for label, field in (("Song", "id"), ("User", "id"), ("Artist", "name"), ("Genre", "name")):
        graph_rows(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{field} IS UNIQUE")
    tracks = list(db.songs.find({}, {"keys": 0}))
    ids = [track["_id"] for track in tracks]
    graph_rows("MATCH (s:Song) WHERE NOT s.id IN $ids DETACH DELETE s", ids=ids)
    graph_rows("MATCH (:Song)-[r:BY_ARTIST|IN_GENRE]->() DELETE r")
    graph_rows(CATALOG_GRAPH, tracks=tracks)
    graph_rows("MATCH (a:Artist) WHERE NOT (a)<-[:BY_ARTIST]-() DELETE a")
    graph_rows("MATCH (g:Genre) WHERE NOT (g)<-[:IN_GENRE]-() DELETE g")
    graph_rows("MERGE (:User {id:$user})", user=USER)
    # If the graph volume is new, replay the latest canonical state for all pairs.
    if not graph_rows("MATCH (m:Projection {id:'spotify-playlist-v1'}) RETURN m.id"):
        db.likes.update_many({}, {"$set": {"pending": True}})
        graph_rows("MERGE (:Projection {id:'spotify-playlist-v1'})")


def sync_loop():
    # Exactly one writer in the single application process shipped with Compose.
    # Only acknowledge the revision actually committed to the graph.
    last_error = None
    while True:
        try:
            if not ready.is_set():
                prepare_graph()
                ready.set()
            batch = list(db.likes.find({"pending": True}).sort("changed_at", 1).limit(64))
            if not batch:
                graph_rows("RETURN 1")
            for item in batch:
                query = SET_LIKE if item["liked"] else CLEAR_LIKE
                rows = graph_rows(query, user=item["user"], song=item["song"])
                if not rows:
                    raise RuntimeError("Entitas graf untuk proyeksi belum tersedia.")
                db.likes.update_one({"_id": item["_id"], "revision": item["revision"]},
                                    {"$set": {"pending": False, "synced_at": utcnow()}})
            last_error = None
            if batch:
                continue
        except Exception as exc:
            if type(exc) != last_error:
                logging.warning("Sinkronisasi tertunda: %s", exc)
            last_error = type(exc)
            ready.clear()
        wake.wait(2)
        wake.clear()
