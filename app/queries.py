# Kueri yang dijalankan aplikasi. Satu titik perantara mewakili artis atau genre.
RELATED = """
MATCH (source:Song {id:$song})-[:BY_ARTIST|IN_GENRE]->(via)<-[:BY_ARTIST|IN_GENRE]-(candidate:Song)
WHERE candidate <> source
RETURN candidate.id AS id, collect(DISTINCT via.name) AS reasons, count(DISTINCT via) AS score
ORDER BY score DESC, id LIMIT 8
"""

RECOMMEND = """
MATCH (u:User {id:$user})-[:LIKES]->(source:Song)
MATCH (source)-[:BY_ARTIST|IN_GENRE]->(via)<-[:BY_ARTIST|IN_GENRE]-(candidate:Song)
WHERE NOT EXISTS { MATCH (u)-[:LIKES]->(candidate) }
RETURN candidate.id AS id, collect(DISTINCT via.name) AS reasons,
       count(DISTINCT [source.id, elementId(via)]) AS score
ORDER BY score DESC, id LIMIT 8
"""

CATALOG_GRAPH = """
UNWIND $tracks AS row
MERGE (s:Song {id:row._id})
SET s.title=row.title, s.album=row.album, s.playlist_position=row.playlist_position
MERGE (g:Genre {name:row.genre})
MERGE (s)-[:IN_GENRE]->(g)
WITH s, row
UNWIND row.artists AS artist_name
MERGE (a:Artist {name:artist_name})
MERGE (s)-[:BY_ARTIST]->(a)
"""

SET_LIKE = """
MATCH (u:User {id:$user}), (s:Song {id:$song})
MERGE (u)-[:LIKES]->(s)
RETURN s.id AS id
"""
CLEAR_LIKE = """
MATCH (u:User {id:$user}), (s:Song {id:$song})
OPTIONAL MATCH (u)-[r:LIKES]->(s)
DELETE r
RETURN s.id AS id
"""
