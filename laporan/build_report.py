from pathlib import Path
from copy import deepcopy
from io import BytesIO
import json, hashlib, zipfile, urllib.request
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'laporan'
REF=Path('/Users/arman/Downloads/Template_Laporan_Project.docx')
assert hashlib.sha256(REF.read_bytes()).hexdigest()=='92effe4484d1881d9e7b641d24695d7f1ae12a09777ec5bc4e1405a4ebc1a902'
d=Document(REF); ps=list(d.paragraphs); tables=list(d.tables)
for i in [15,16,17,21,25,27]:
 pr=ps[i]._p.get_or_add_pPr()
 for child in list(pr):
  if child.tag==qn('w:numPr'):pr.remove(child)

def put(i,text):
 p=ps[i]; p.text=text; return p
def after(anchor,text='',style='Normal',code=False):
 p=d.add_paragraph(text,style); anchor._p.addnext(p._p)
 if code:
  p.paragraph_format.space_before=Pt(0); p.paragraph_format.space_after=Pt(0)
  p.paragraph_format.line_spacing=1
  p.paragraph_format.left_indent=Pt(0);p.paragraph_format.first_line_indent=Pt(0)
  for r in p.runs: r.font.name='Liberation Mono';r.font.size=Pt(9)
 return p
def extend(i,items):
 anchor=ps[i]
 for item in items:
  if isinstance(item,tuple):
   kind,text=item
   if kind=='code':
    lines=text.strip().splitlines()
    for index,line in enumerate(lines):
     anchor=after(anchor,line,code=True)
     anchor.paragraph_format.keep_with_next=len(lines)<35 and index<len(lines)-1
    anchor=after(anchor,'')
   elif kind=='image':
    p=after(anchor);p.add_run().add_picture(str(ROOT/'bukti'/text),width=Inches(6));anchor=p
   else: anchor=after(anchor,text,kind)
  else: anchor=after(anchor,item)
 return anchor
def tablefill(t,rows,widths):
 while len(t.rows)<len(rows)+1: t._tbl.append(deepcopy(t.rows[-1]._tr))
 for row,values in zip(t.rows[1:],rows):
  for c,v in zip(row.cells,values): c.text=v
 for row in t.rows:
  pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
  for c,w in zip(row.cells,widths):
   c.width=Inches(w)
   for p in c.paragraphs:
    p.paragraph_format.space_after=Pt(4);p.paragraph_format.space_before=Pt(4)
    for r in p.runs:r.font.size=Pt(10)
 for col,w in zip(t.columns,widths):col.width=Inches(w)
 t.autofit=False
 t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))

put(0,'Ruang Nada\nArsitektur Polyglot Persistence\nMongoDB dan Neo4j')
put(2,'Link Repositori Kode (GitHub/GitLab): [Lengkapi tautan repositori]\nFile Docker Compose: TBDNR_PROJEK/docker-compose.yml')
ps[2].paragraph_format.space_before=Pt(12)
for i in [3,11,18,28,31]:ps[i].paragraph_format.page_break_before=True
put(5,'Ruang Nada merupakan prototipe platform musik untuk mendemonstrasikan arsitektur basis data nonrelasional. Kebutuhan katalog, profil, playlist, dan status suka ditangani MongoDB, sedangkan penelusuran hubungan lagu, artis, genre, dan pengguna ditangani Neo4j. Pembagian ini menerapkan polyglot persistence: pemilihan model penyimpanan disesuaikan dengan pola akses masing-masing modul.')
extend(5,[
'Tujuan proyek adalah memodelkan aggregate dokumen, membentuk graph relasi, menjalankan kueri lintas database, dan menjaga agar perubahan suka di MongoDB akhirnya tercermin di Neo4j. Antarmuka web berfungsi sebagai sarana demonstrasi alur data.',
'Dataset operasional berisi 50 lagu, 64 nama artis unik, 47 nama album, dan enam genre. Metadata katalog berasal dari dataset playlist “Ini gue” yang dicatat proyek. Genre merupakan klasifikasi luas untuk demonstrasi. Pemutar menggunakan instrumental sintetis lokal sepanjang 12 detik, bukan rekaman asli lagu Spotify.',
'Cakupan meliputi satu pengguna demo, pencarian katalog, sampel audio, pengelolaan beberapa playlist, suka/batal suka, lagu terkait, dan rekomendasi personal berbasis relasi. Login multipengguna, session store, Redis, riwayat dengar, sharding, dan replikasi antarnode belum diimplementasikan.'
])
put(8,'Kebutuhan fungsional dikelompokkan sesuai modul yang tersedia pada aplikasi:')
extend(8,[
'1. Profil: menampilkan dan mengubah nama serta bio pengguna pendengar-demo.',
'2. Katalog dan pemutar: mencari judul, artis, album, atau genre; memfilter genre; membaca detail lagu; serta memutar, menjeda, dan berpindah antar-sampel lokal.',
'3. Playlist: membuat beberapa playlist, mengganti nama, menambahkan atau mengeluarkan lagu, mengubah urutan, dan menghapus playlist. Setiap playlist memuat paling banyak 200 ID lagu unik.',
'4. Interaksi suka: menyimpan status liked terbaru untuk setiap pasangan pengguna–lagu, menampilkan lagu disukai, dan meneruskan perubahan ke graph.',
'5. Penemuan musik: menampilkan lagu terkait berdasarkan artis/genre serta rekomendasi personal berdasarkan lagu yang disukai. Kandidat personal mengecualikan lagu yang sudah disukai dan dibatasi delapan hasil.',
'Rilisan pilihan dan Stasiun Berdasarkan Artis pada Home menggunakan katalog MongoDB. Keduanya bukan hasil rekomendasi personal Neo4j. Rekomendasi Neo4j ditampilkan melalui panel Lagu terkait dan Untukmu.'
])
put(10,'Tabel berikut menyatakan pola akses yang dirancang, bukan hasil pengukuran trafik produksi. Data likes mencatat keadaan terakhir dan waktu perubahan; collection ini bukan log seluruh peristiwa ataupun collection time-series.')
tablefill(tables[1],[
['Profil','Identitas, nama, dan bio dalam satu dokumen.','Baca/ubah berdasarkan _id.'],
['Katalog','Metadata lagu dan array artists; bentuk dokumen aggregate.','Dominan baca; awalan keys, filter genre, urutan katalog.'],
['Playlist','Pemilik, nama, array ID lagu berurutan, version.','Baca berdasarkan owner; ubah atomik satu dokumen.'],
['Suka dan sinkronisasi','Status liked, pending, revision, waktu perubahan/sinkron.','Upsert per pasangan; worker membaca pending=true.'],
['Rekomendasi','User, Song, Artist, Genre dan relasinya; sangat terhubung.','Traversal beberapa relasi, skor, dan pengambilan metadata.'],
['Sampel audio','File WAV lokal; dokumen hanya menyimpan path/durasi.','Baca file melalui HTTP saat Play.']
],[1.15,2.45,2.4])

put(13,'2.1.1 Modul katalog profil playlist dan suka pada MongoDB')
put(14,'MongoDB dipilih karena objek yang dibaca bersama dapat disimpan sebagai dokumen. Database ruangnada memiliki collection songs, users, playlists, dan likes. Model dibuat mengikuti kebutuhan kueri; skema yang fleksibel tetap disertai pemeriksaan tipe, panjang input, dan referensi ID pada API.')
put(15,'Model aggregate dan batas dokumen')
ps[15].style='Heading 2'
put(16,'Contoh dokumen songs berikut diambil dari database operasional. Satu dokumen membungkus metadata satu lagu, sedangkan array artists menyimpan nama artis terpisah untuk proyeksi graph. Field artist merupakan teks siap tampil; keys merupakan data turunan untuk pencarian.')
ps[16].style='Normal'
song=json.load(urllib.request.urlopen('http://localhost:8088/api/songs/2bJvI42r8EF3wxjOuDav4r'))['song']
# API sengaja tidak mengirim keys; gunakan nilai yang diverifikasi pada database.
song['keys']=['globalization','hip-hop','lives','ne-yo','of','our','pitbull,','pitbull, ne-yo','time','time of our lives']
extend(16,[('code',json.dumps(song,ensure_ascii=False,indent=2)),
'original_duration_ms menyimpan durasi asli 229.358 ms, sekitar 3 menit 49 detik. seconds=12 menyimpan durasi sampel yang benar-benar diputar. cover adalah kode artwork lokal. playlist_position adalah urutan katalog sumber, bukan urutan lagu pada playlist pengguna. Field spotify_id, spotify_url, release_year, dan explicit sudah tidak disimpan dalam dokumen songs.',
'Playlist merupakan aggregate terpisah: nama, pemilik, urutan ID lagu, dan versi diperbarui dalam satu dokumen. Metadata lagu direferensikan melalui ID agar perubahan katalog tidak memerlukan penyalinan ke setiap playlist. Contoh aktual:',
('code',json.dumps(json.load(urllib.request.urlopen('http://localhost:8088/api/playlists'))['playlists'][0],indent=2)),
'Profil tersimpan sebagai {"_id":"pendengar-demo","name":"Pendengar Demo","bio":""}. Status suka menggunakan _id gabungan user/song sehingga satu pasangan hanya memiliki satu dokumen. Contoh berikut menampilkan field inti, tanpa timestamp:',
('code','{\n  "_id": "pendengar-demo/2bJvI42r8EF3wxjOuDav4r",\n  "user": "pendengar-demo",\n  "song": "2bJvI42r8EF3wxjOuDav4r",\n  "liked": true, "pending": false, "revision": 1\n}'),
'Dokumen likes juga menyimpan changed_at dan synced_at bertipe tanggal. liked=false berarti suka dibatalkan, sedangkan pending=false berarti revisi terakhir telah dikonfirmasi tersinkron. Dokumen tetap disimpan saat batal suka untuk membawa status terakhir ke graph; dokumen tersebut bukan suka aktif.',
'Indeks MongoDB: songs memiliki indeks keys (multikey), genre, dan playlist_position; playlists memiliki indeks gabungan owner–name; likes memiliki indeks pending–changed_at dan user–liked. Semua collection juga memiliki indeks unik _id bawaan. Ketersediaan indeks belum membuktikan peningkatan latensi; proyek belum menyertakan benchmark explain/latensi terukur.'
])
put(17,'2.1.2 Modul relasi dan rekomendasi pada Neo4j')
ps[17].style='Heading 2'
extend(17,[
'Neo4j dipilih karena rekomendasi membutuhkan penelusuran hubungan dari lagu sumber menuju artis atau genre yang sama. MongoDB tetap menjadi sumber data utama; graph menyimpan proyeksi untuk kebutuhan traversal. Hasil Cypher berupa ID kandidat, alasan, dan skor, kemudian backend mengambil metadata lengkap dari MongoDB.',
'Entitas domain: User memiliki id; Song memiliki id, title, album, playlist_position; Artist dan Genre masing-masing memiliki name. Uniqueness constraint diterapkan pada User.id, Song.id, Artist.name, dan Genre.name. Album masih berupa properti Song, bukan node tersendiri.',
('code','(User)-[:LIKES]->(Song)\n(Song)-[:BY_ARTIST]->(Artist)\n(Song)-[:IN_GENRE]->(Genre)'),
'Satu pengguna dapat menyukai banyak lagu dan satu lagu dapat disukai banyak pengguna pada model graph, meskipun aplikasi sekarang hanya memakai satu pengguna demo. Lagu dapat memiliki beberapa artis; setiap lagu dataset memiliki satu genre. Artist dan Genre dapat dihubungkan oleh banyak Song.',
'Identitas bersama adalah songs._id = Song.id serta users._id = User.id. Pada pemeriksaan 24 November 2026 terdapat 50 Song, 64 Artist, 6 Genre, 1 User, dan 2 node teknis Projection. Total 123 node mencakup node teknis tersebut. Relasi berjumlah 138: 84 BY_ARTIST, 50 IN_GENRE, dan 4 LIKES. Projection digunakan sebagai penanda inisialisasi/proyeksi dan tidak ikut menilai rekomendasi.',
'2.1.3 Alur integrasi dan konsistensi',
'Browser mengakses API Flask. API membaca/menulis MongoDB dan menjalankan Cypher melalui driver Neo4j. Worker berupa satu thread di proses aplikasi, bukan service Redis atau container terpisah. MongoDB dan Neo4j masing-masing berjalan pada satu container dengan volume persisten.',
'Pada aksi suka, API menyimpan liked, revision, dan pending dalam satu operasi dokumen atomik. Worker membaca maksimal 64 dokumen tertunda dengan urutan changed_at, lalu membentuk LIKES menggunakan MERGE atau menghapus LIKES untuk batal suka. Setelah berhasil, worker mengubah pending=false hanya jika revision masih sama. Bila revisi telah berubah, pekerjaan revisi baru tetap tertunda.',
'Konsistensi lintas database bersifat eventual consistency. Pembacaan suka pada aplikasi berasal dari MongoDB, sedangkan rekomendasi dapat tertinggal sampai proyeksi selesai. Tidak ada transaksi atomik bersama MongoDB–Neo4j. Worker dibangunkan oleh event dan mencoba kembali melalui jeda tunggu maksimal dua detik saat idle; angka ini bukan jaminan waktu sinkronisasi.',
'Playlist memakai optimistic concurrency control: operasi ubah/hapus mencocokkan _id, owner, dan version. Versi naik setelah pembaruan berhasil; versi lama menghasilkan HTTP 409. Penulisan MongoDB memakai w=1 dan j=true untuk pengakuan jurnal lokal, bukan majority replication.'
])

put(20,'Lingkungan terdiri dari app, mongo, dan neo4j. App menggunakan Python 3.12, Flask 3.1.2, PyMongo 4.15.5, driver Neo4j 5.28.2, dan Waitress 3.0.2. Berikut isi docker-compose.yml proyek; image database dikunci dengan digest.')
put(21,'')
ps[21].style='Normal'
extend(21,[('code',(ROOT/'docker-compose.yml').read_text()),
'Jalankan docker compose up -d --build dari direktori proyek. Aplikasi tersedia di http://localhost:8088; Compass memakai mongodb://localhost:27028/ruangnada; Neo4j Browser di http://localhost:17474 dengan koneksi bolt://localhost:17687. Kata sandi default pada Compose hanya digunakan untuk demonstrasi lokal.',
'Port dipetakan ke 127.0.0.1. Volume dokumen dan graf mempertahankan data saat container dimulai ulang. Compose menunggu healthcheck MongoDB; kesiapan graph ditangani worker aplikasi karena depends_on Neo4j menggunakan service_started. Jangan memakai docker compose down -v jika data demo perlu dipertahankan.'
])
put(23,'Potongan berikut berasal dari app/server.py, app/database.py, dan app/queries.py. Variabel db adalah database ruangnada; USER bernilai pendengar-demo. Parameter kueri berasal dari backend dan tidak disusun melalui interpolasi input pengguna.')
put(24,'A. Kueri pada Database 1 (MongoDB)')
put(25,'Pencarian katalog dan pengambilan metadata kandidat')
ps[25].style='Normal'
extend(25,[('code','query = {}\nif term:\n    query["keys"] = {"$regex": "^" + re.escape(term)}\nif genre:\n    query["genre"] = genre\nsongs = list(db.songs.find(query, CATALOG_FIELDS)\n             .sort("playlist_position", 1))'),
'Endpoint GET /api/catalog menormalkan kata pencarian menjadi huruf kecil, membatasi panjang input, lalu mencari awalan pada keys. CATALOG_FIELDS={"keys":0} menyembunyikan field pencarian dari respons. Setelah Neo4j mengembalikan kandidat, fungsi hydrate membaca songs dengan _id dalam daftar kandidat dan menyusun ulang hasil sesuai urutan skor Cypher.',
('code','found = {s["_id"]: s for s in db.songs.find(\n    {"_id": {"$in": [r["id"] for r in rows]}},\n    CATALOG_FIELDS)}\nreturn [dict(found[r["id"]],\n             reasons=sorted(r["reasons"]), score=r["score"])\n        for r in rows if r["id"] in found]'),
'Penyimpanan status suka dan penanda sinkronisasi',
('code','key = USER + "/" + song\nchanged = {"$ne": [{"$ifNull": ["$liked", None]}, liked]}\nresult = db.likes.find_one_and_update(\n    {"_id": key}, [{"$set": {\n        "user": USER, "song": song, "liked": liked,\n        "pending": {"$cond": [changed, True, "$pending"]},\n        "revision": {"$add": [\n            {"$ifNull": ["$revision", 0]},\n            {"$cond": [changed, 1, 0]}]},\n        "changed_at": {"$cond": [\n            changed, "$$NOW", "$changed_at"]}\n    }}], upsert=True,\n    return_document=ReturnDocument.AFTER)'),
'Update pipeline di atas menambah revisi hanya ketika status berubah. Permintaan berulang dengan nilai liked yang sama tidak menambah revisi. liked dan pending disimpan bersama sehingga pekerjaan sinkronisasi tidak hanya bergantung pada memori proses.',
'Pembuatan dan pembaruan playlist',
('code','record = {"_id": uuid.uuid4().hex, "owner": USER,\n          "name": name, "songs": [], "version": 1}\ndb.playlists.insert_one(record)\n\nkey = {"_id": pid, "owner": USER, "version": version}\nchanged = db.playlists.find_one_and_update(\n    key, {"$set": {"name": name, "songs": ids},\n          "$inc": {"version": 1}},\n    return_document=ReturnDocument.AFTER)'),
'Sebelum pembaruan, API memastikan ID lagu valid, tidak duplikat, dan tidak melebihi 200 lagu. Jika dokumen masih ada tetapi versinya berbeda, API menolak dengan HTTP 409. Penghapusan juga memakai filter versi yang sama.'
])
put(26,'B. Kueri pada Database 2 (Neo4j)')
put(27,'Pembentukan relasi katalog dan status suka')
ps[27].style='Normal'
import sys
sys.path.insert(0,str(ROOT/'app'))
from queries import CATALOG_GRAPH, SET_LIKE, CLEAR_LIKE, RELATED, RECOMMEND
extend(27,[('code',CATALOG_GRAPH),
'UNWIND memproses setiap lagu dan nama artisnya. MERGE menggunakan identitas yang sama dengan MongoDB agar node dan hubungan katalog tidak digandakan saat inisialisasi ulang.',
('code',SET_LIKE),('code',CLEAR_LIKE),
'Worker memilih kueri suka atau batal suka sesuai nilai liked di MongoDB. MERGE membentuk satu hubungan yang sesuai; OPTIONAL MATCH memungkinkan batal suka tetap aman ketika hubungan sudah tidak ada.',
'Lagu terkait berdasarkan artis atau genre',('code',RELATED),
'Kueri menelusuri penghubung Artist atau Genre yang sama, mengecualikan lagu sumber, menghitung jumlah penghubung berbeda sebagai score, lalu membatasi delapan hasil. Untuk Time of Our Lives, Give Me Everything mempunyai tiga penghubung: Pitbull, Ne-Yo, dan Hip-Hop; hasil pemeriksaan terbaru menunjukkan score=3.',
'Rekomendasi personal berdasarkan suka',('code',RECOMMEND),
'Kueri berawal dari LIKES pengguna. Kandidat yang sudah disukai dikeluarkan. Skor menghitung pasangan berbeda antara lagu sumber dan node penghubung; score bukan probabilitas kecocokan. Urutan ditentukan score menurun, kemudian ID untuk hasil yang konsisten. Tanpa LIKES, kueri ini menghasilkan daftar kosong. Model tidak memakai machine learning atau perilaku pengguna lain.'
])

put(30,'Dua alur end-to-end diuji melalui aplikasi, MongoDB, dan Neo4j. Screenshot pada Gambar 4.1–4.4 merupakan bukti proyek tersimpan tanggal 20 November 2026. Pemeriksaan baca ulang tanggal 24 November 2026 dituliskan terpisah agar kondisi awal pengujian tidak disamakan dengan keadaan akun sekarang.')
tablefill(tables[2],[
['TC-01','Cari lagu lalu tampilkan lagu terkait.','MongoDB dan Neo4j','Lulus pada log. Pencarian dan kandidat pada Gambar 4.1; baca ulang score=3.'],
['TC-02','Suka, sinkronisasi LIKES, rekomendasi, lalu batal suka.','MongoDB dan Neo4j','Lulus pada log. Gambar 4.2–4.4 memperlihatkan kondisi sebelum/sesudah dan graph.']
],[.55,1.8,1.1,2.55])
# Sisipkan uraian sesudah tabel pengujian.
anchor=d.add_paragraph();tables[2]._tbl.addnext(anchor._p)
def testtext(text,style='Normal'):
 global anchor
 anchor=after(anchor,text,style)
def pic(name,caption):
 global anchor
 anchor=after(anchor);anchor.add_run().add_picture(str(ROOT/'bukti'/name),width=Inches(6))
 anchor.paragraph_format.left_indent=Pt(0);anchor.paragraph_format.first_line_indent=Pt(0)
 anchor.alignment=1
 anchor.paragraph_format.keep_with_next=True
 testtext(caption)
testtext('TC-01 Pencarian katalog dan lagu terkait','Heading 2')
testtext('Langkah: buka Search, cari “Time”, pilih Time of Our Lives, lalu lihat Lagu terkait. MongoDB menemukan lagu sumber; Neo4j menelusuri artis/genre yang sama; MongoDB melengkapi detail kandidat untuk UI. Give Me Everything ditampilkan melalui Pitbull, Ne-Yo, dan Hip-Hop. Pemeriksaan GET /api/songs/2bJvI42r8EF3wxjOuDav4r/related pada 24 November menghasilkan kandidat tersebut dengan score 3 dan alasan yang sama.')
pic('TC-01-katalog-dan-graf.jpg','Gambar 4.1 Hasil pencarian dan daftar lagu terkait pada aplikasi, bukti 20 November 2026.')
testtext('TC-02 Suka dan rekomendasi personal','Heading 2')
testtext('Prasyarat demonstrasi terdahulu adalah akun dengan status suka terkendali: kandidat Give Me Everything belum disukai dan belum direkomendasikan. Langkah: sukai Time of Our Lives, tunggu pending menjadi nol, periksa Untukmu dan graph, lalu batalkan suka. MongoDB menyimpan liked/pending; worker memperbarui LIKES; Neo4j menghitung kandidat; MongoDB menyediakan metadata hasil.')
testtext('Log uji mencatat sepuluh PUT suka bersamaan menghasilkan satu revisi yang sama dan satu LIKES. Setelah batal suka, LIKES terhapus dan kandidat uji tidak lagi muncul pada kondisi pengujian tersebut. Efek hilangnya kandidat tidak berlaku mutlak: kandidat masih dapat muncul bila terhubung melalui lagu lain yang tetap disukai.')
pic('TC-02-sebelum-suka.jpg','Gambar 4.2 Panel Untukmu sebelum suka pada skenario terkendali, bukti 20 November 2026.')
pic('TC-02-sesudah-suka.jpg','Gambar 4.3 Rekomendasi sesudah suka dan sinkronisasi, bukti 20 November 2026.')
pic('TC-02-graf-neo4j.jpg','Gambar 4.4 Jalur User–LIKES–Song–Artist–Song dalam Neo4j Browser, bukti 20 November 2026.')
testtext('Pemeriksaan kondisi terkini','Heading 2')
testtext('Pada 24 November 2026, /api/status mengembalikan {"graph":true,"mongo":true,"pending":0}. MongoDB berisi 50 songs, 1 users, 1 playlists, dan 5 dokumen likes. Empat dokumen memiliki liked=true dan satu liked=false. Graph mempunyai empat LIKES; jumlah dokumen likes tidak sama dengan jumlah suka aktif karena dokumen batal suka tetap disimpan.')
testtext('GET /api/recommendations menghasilkan delapan kandidat. Low, Stereo Hearts, Can’t Hold Us, Empire State Of Mind, Whistle, No Lie, dan Club Can’t Handle Me masing-masing memiliki score 4 melalui Hip-Hop; Die Young memiliki score 1 melalui Kesha. Time of Our Lives dan Give Me Everything tidak ada dalam hasil personal karena keduanya sudah disukai. Hal ini berbeda dari TC-02 terdahulu yang memakai kondisi awal terkendali.')
testtext('Bukti pengujian tambahan dan batas pengujian','Heading 2')
testtext('File bukti/integrasi.txt mencatat kelulusan urutan playlist, penolakan versi usang, ID lagu ganda, tipe liked yang salah, serta ID lagu tidak ditemukan. Log juga mencatat bahwa suka tetap disimpan saat Neo4j berhenti, pending bertahan setelah restart aplikasi, dan satu LIKES terbentuk setelah pemulihan dengan nol pekerjaan tertunda. Hasil tersebut adalah arsip pengujian; uji gangguan tidak dijalankan ulang pada pemeriksaan baca tanggal 24 November.')
testtext('Skrip pengujian tersedia di uji/integrasi.py. Sebelum mengulang TC-02, kondisi seluruh suka pengguna perlu dikendalikan: skrip hanya menonaktifkan dua lagu uji, sehingga suka lain dapat membuat asumsi “kandidat belum direkomendasikan” tidak terpenuhi. Simpan dan pulihkan status akun saat demonstrasi. Tidak tersedia benchmark latensi, throughput, beban produksi, atau pengujian multi-instance; laporan ini tidak mengklaim hasil pengukuran tersebut.')

put(32,'1. Kelebihan dan Tantangan Implementasi')
extend(32,[
'Kelebihan. MongoDB menyatukan data yang dibaca bersama dalam dokumen dan menjaga pembaruan playlist serta status suka dalam batas satu dokumen. Neo4j menyatakan relasi artis/genre secara eksplisit sehingga alasan rekomendasi dapat ditelusuri. Penggabungan ID kandidat graph dengan metadata MongoDB memperlihatkan penggunaan kedua database dalam satu alur aplikasi.',
'Mekanisme pending dan revision memungkinkan status suka disimpan sebelum graph tersedia. MERGE dan pemeriksaan revisi pada acknowledgment membantu pengulangan sinkronisasi tanpa menghasilkan LIKES ganda atau menghapus pekerjaan revisi lebih baru. Volume Docker mempertahankan data antarrestart. Keuntungan ini telah didemonstrasikan secara fungsional; belum ada perbandingan performa kuantitatif dengan arsitektur satu database.',
'Tantangan. Rekomendasi dapat tertinggal selama eventual consistency. Sistem memiliki dua penyimpanan dan memerlukan pengawasan koneksi serta pemulihan graph. Worker dirancang sebagai satu penulis dalam satu proses aplikasi; menambah beberapa instance membutuhkan koordinasi pekerjaan atau kontrol versi pada graph. Inisialisasi menulis ulang proyeksi katalog, sehingga bukan mekanisme sinkronisasi katalog online berskala besar.',
'Keterbatasan. Hanya satu akun demo yang dipakai tanpa autentikasi. Klasifikasi genre yang luas dapat menghasilkan kandidat dengan alasan umum. Nama artis digunakan sebagai identitas unik sehingga variasi penulisan harus dibersihkan. Audio adalah sampel sintetis, sampul adalah artwork lokal, dan katalog belum dapat diedit melalui UI. likes menyimpan keadaan terakhir, bukan riwayat lengkap setiap klik.',
'2. Kesimpulan',
'Ruang Nada telah mengimplementasikan polyglot persistence melalui MongoDB sebagai penyimpanan dokumen utama dan Neo4j sebagai proyeksi relasi untuk rekomendasi. Aggregate playlist, referensi ID lagu, indeks pencarian, uniqueness constraint, optimistic concurrency control, dan sinkronisasi eventual consistency merupakan bagian arsitektur yang dapat dijelaskan melalui kode dan bukti pengujian.',
'Dua skenario utama menghubungkan kedua database: pencarian menuju lagu terkait, serta suka menuju rekomendasi personal. Pemeriksaan terbaru menunjukkan 50 lagu, empat relasi suka aktif, dan nol pembaruan tertunda. Pengembangan berikutnya dapat mencakup login multipengguna, evaluasi kualitas rekomendasi, pengukuran performa, dan koordinasi worker. Redis belum diperlukan oleh implementasi yang ada.',
'Sumber implementasi dan bukti',
'Konfigurasi: docker-compose.yml dan app/requirements.txt. Pemodelan dan sinkronisasi: app/database.py. Kueri graph: app/queries.py. Endpoint dan validasi: app/server.py. Dataset dan audio: app/catalog.json serta app/audio_samples.py. Antarmuka: app/static/app.js, index.html, style.css. Bukti: bukti/TC-01-katalog-dan-graf.jpg, TC-02-sebelum-suka.jpg, TC-02-sesudah-suka.jpg, TC-02-graf-neo4j.jpg, integrasi.txt. Skrip uji: uji/integrasi.py.'
])
# Cegah judul/label subbagian terpisah dari paragraf sesudahnya.
for p in d.paragraphs:
 if p.text.startswith(('2.1.','1.2.1','1.2.2','A. Kueri','B. Kueri')) or p.text in ['2. Kesimpulan','Sumber implementasi dan bukti','Penyimpanan status suka dan penanda sinkronisasi','Pembuatan dan pembaruan playlist','Pembentukan relasi katalog dan status suka','Lagu terkait berdasarkan artis atau genre','Rekomendasi personal berdasarkan suka']:
  p.paragraph_format.keep_with_next=True
bio=BytesIO();d.save(bio)
# Pertahankan package sumber selain bagian isi dan relasi gambar tambahan.
with zipfile.ZipFile(REF) as src, zipfile.ZipFile(BytesIO(bio.getvalue())) as gen:
 inventory={n:{'size':len(src.read(n)),'sha256':hashlib.sha256(src.read(n)).hexdigest()} for n in src.namelist()}
 (OUT/'qa/package-inventory.json').write_text(json.dumps(inventory,indent=2))
 allowed={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
 with zipfile.ZipFile(OUT/'Laporan_Project_Ruang_Nada.docx','w',zipfile.ZIP_DEFLATED) as target:
  for n in src.namelist():target.writestr(n,gen.read(n) if n in allowed else src.read(n))
  for n in gen.namelist():
   if n not in src.namelist():target.writestr(n,gen.read(n))
 with zipfile.ZipFile(OUT/'Laporan_Project_Ruang_Nada.docx') as final:
  assert all(src.read(n)==final.read(n) for n in src.namelist() if n not in allowed)
print(OUT/'Laporan_Project_Ruang_Nada.docx')
