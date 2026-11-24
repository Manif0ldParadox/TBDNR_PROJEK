# Ruang Nada

Prototipe lokal platform musik untuk tugas akhir Teknologi Basis Data Non Relasional. MongoDB menyimpan data utama. Neo4j menelusuri hubungan untuk menjelaskan mengapa sebuah lagu direkomendasikan. Antarmuka memakai satu akun demo dan 50 lagu nyata dengan metadata dari 50 posisi pertama playlist Spotify [Ini gue](https://open.spotify.com/playlist/3DCgQi710f8kSDdRHB350V). Rekaman Spotify tidak disalin. Setiap lagu memakai sampel instrumental lokal orisinal sepanjang 12 detik untuk demonstrasi pemutar.

## Menjalankan

Aktifkan Docker Desktop, lalu jalankan dari folder yang berisi file ini.

```sh
docker compose up -d --build
docker compose ps
```

Buka [aplikasi Ruang Nada](http://localhost:8088). Klik **Jejak database** di bawah rekomendasi untuk melihat status. Saat pertama dijalankan, tunggu **Neo4j siap**. MongoDB dan Neo4j memakai volume lokal. Untuk mengakhiri demo dan menyimpan isinya, jalankan `docker compose stop`. Untuk melanjutkan gunakan `docker compose up -d`.

| Akses lokal | Alamat dan pengaturan |
| --- | --- |
| Aplikasi | `http://localhost:8088` |
| MongoDB Compass | URI `mongodb://localhost:27028`, database `ruangnada` |
| Neo4j Browser | `http://localhost:17474`, koneksi `bolt://localhost:17687`, nama pengguna `neo4j`, kata sandi demo `ruangnada-demo` |

Seluruh port terikat pada loopback. Topologi demo terdiri dari satu proses aplikasi, satu MongoDB standalone dan satu Neo4j Community. Setiap database menyimpan datanya di volume tersendiri. Konfigurasi layanan ada di [docker-compose.yml](docker-compose.yml).

## Cara mendemonstrasikan

| Uji | Tindakan | Yang diamati |
| --- | --- | --- |
| TC-01 · Katalog ke graf | Buka **Search**, cari **Time**, pilih **Time of Our Lives**, lalu buka **Lagu terkait**. | MongoDB menemukan lagu sumber, Neo4j menemukan **Give Me Everything** melalui artis Pitbull dan Ne-Yo serta genre Hip-Hop, lalu MongoDB melengkapi metadata kandidat. |
| TC-02 · Suka ke rekomendasi | Mulai dengan **Time of Our Lives** dan **Give Me Everything** dalam keadaan belum disukai. Buka **Untukmu**, sukai **Time of Our Lives**, tunggu angka tertunda menjadi nol, lalu batalkan suka. | **Give Me Everything** muncul setelah sinkronisasi dan menghilang setelah batal suka. Akun tetap bisa membaca status sukanya langsung dari MongoDB. |
| Pemulihan | Jalankan `docker compose stop neo4j`. Saat status graf menunggu, sukai **Time of Our Lives**. Jalankan `docker compose start neo4j`. | Saat graf berhenti, suka tetap tersimpan, jumlah tertunda naik dan panel rekomendasi menampilkan status layanan. Setelah graf siap, antrean terkirim dan rekomendasi muncul. |

Halaman **Home** menampilkan filter genre, pilihan cepat, rilisan, dan **Stasiun Berdasarkan Artis** yang seluruhnya memakai data katalog MongoDB. Bagian stasiun mengelompokkan lagu berdasarkan artis dan bukan rekomendasi personal. Klik kartu stasiun untuk membuka hero artis, tombol putar, serta daftar lagu dan album yang melibatkan artis tersebut. Menu **Create** dapat membuat banyak playlist. Setiap playlist langsung muncul secara alfabetis di sidebar kiri pada laptop dan dapat dibuka sebagai halaman detail tersendiri. Halaman detail playlist menyediakan hero, cover mosaik, tombol putar, pencarian lagu, tambah/hapus lagu, pengurutan isi, penggantian nama, dan penghapusan playlist. **Your Library** menampilkan lagu disukai dan seluruh playlist sebagai kartu-kartu persegi yang rapi. Profil berada di bagian paling bawah sidebar kiri pada laptop dan di halaman **Your Library** pada ponsel. Tekan lagu untuk memulai sampel lokal dan menampilkan kartu pemutar di atas navigasi. Jeda mempertahankan kartu, dan kartu tertutup saat sampel selesai.

Pada lebar jendela 960 piksel ke atas, menu berada di kiri, kolom pencarian di atas, dan rekomendasi di kanan. Pada jendela yang lebih sempit, empat menu berada di bawah. Klik sampul album untuk menyaring daftar lagu, lalu klik judul lagu untuk memutar sampel. Kartu pemutar menyediakan kontrol jeda, posisi putar, perpindahan lagu, dan suka.

## Bukti untuk BAB 4

Uji lokal menggunakan MongoDB 8.0.38 dan Neo4j Community 5.26.33. Screenshot diambil dari aplikasi dan Neo4j Browser yang terhubung ke layanan Docker tersebut.

| Skenario | Hasil teramati | Bukti |
| --- | --- | --- |
| Dataset katalog | MongoDB memuat 50 lagu dalam urutan playlist sumber, sedangkan enam lagu contoh sebelumnya sudah tidak ada. | [Home dengan dataset 50 lagu](bukti/Dataset-50-lagu.jpg) |
| TC-01 | Pencarian Time menemukan Time of Our Lives. Penelusuran graf mengembalikan Give Me Everything melalui Pitbull, Ne-Yo, dan Hip-Hop. | [Pencarian dan hasil graf](bukti/TC-01-katalog-dan-graf.jpg) |
| TC-02 | Give Me Everything muncul di Untukmu setelah Time of Our Lives disukai. Graf memperlihatkan relasi LIKES dan hubungan artis serta genre. Batal suka menghapus relasi LIKES dan rekomendasi tersebut. | [Sebelum suka](bukti/TC-02-sebelum-suka.jpg) · [Sesudah suka](bukti/TC-02-sesudah-suka.jpg) · [Neo4j Browser](bukti/TC-02-graf-neo4j.jpg) |
| Pemulihan dan akses serentak | Sepuluh permintaan suka bersamaan menghasilkan satu relasi. Perubahan saat Neo4j offline tetap tertunda setelah aplikasi dimulai ulang, kemudian terkirim ketika graf siap. | [Log uji langsung](bukti/integrasi.txt) |

Tampilan responsif juga diperiksa di Chrome dengan viewport desktop dan seluler. [Hasil uji antarmuka](bukti/antarmuka.txt)

## Model data dan alasan pemilihan

| Operasi | Representasi | Pola akses dan alasan desain |
| --- | --- | --- |
| Edit profil | `users` di MongoDB | Baca dan ubah satu dokumen berdasarkan ID akun. |
| Cari dan dengar lagu | `songs` di MongoDB | Satu dokumen memuat judul, daftar artis, album, genre, metadata sumber Spotify, durasi asli, dan referensi WAV demo. Pencarian memakai awalan judul, artis, album, genre, atau kata di dalamnya. Indeks multikey pada `keys` dan indeks `genre` disediakan untuk kuerinya. |
| Kelola playlist | `playlists` di MongoDB | Nama, ID pemilik, dan array ID lagu berurutan dibaca bersama. Simpan dan hapus memeriksa `version` supaya edit dari tab lain tidak tertimpa diam-diam. |
| Sukai lagu | `likes` di MongoDB | Satu dokumen untuk satu pasangan pengguna–lagu, dengan ID gabungan, status, revisi dan tanda pengiriman. Dokumen tetap ada setelah batal suka untuk mencatat keadaan terakhir. |
| Lagu terkait | `Song`, `Artist`, `Genre` di Neo4j | Telusuri artis atau genre yang sama. Kandidat diurutkan menurut jumlah penghubung berbeda, kemudian ID lagu. |
| Rekomendasi pribadi | `User` dan relasi `LIKES` di Neo4j | Telusuri dari lagu yang disukai ke kandidat, kecualikan lagu yang sudah disukai. Skor menghitung pasangan lagu sumber dan penghubung yang berbeda. |

Satu lagu dapat memiliki banyak artis dan satu klasifikasi genre luas untuk kebutuhan demonstrasi. Setiap nilai pada array `artists` menjadi node `Artist` tersendiri sehingga kolaborasi dapat menghasilkan hubungan rekomendasi yang benar. Album dan metadata sumber disimpan di MongoDB. Identitas bersama adalah `songs._id = Song.id` dan `users._id = User.id`. Graf memakai constraint unik pada ID pengguna dan lagu, serta nama genre dan artis. Katalog dikelola melalui data awal proyek. Tidak ada operasi edit katalog pada UI.

Contoh bentuk dokumen playlist setelah pendengar menambahkan dua lagu (nilai ID playlist disingkat).

```json
{"_id":"p1","owner":"pendengar-demo","name":"Party Mix","songs":["2bJvI42r8EF3wxjOuDav4r","4QNpBfC0zvjKqPJcyqBy9W"],"version":2}
```

Salah satu jalur graf yang dipakai untuk merekomendasikan **Give Me Everything** setelah **Time of Our Lives** disukai.

```text
(:User {id:"pendengar-demo"})-[:LIKES]->(:Song {id:"2bJvI42r8EF3wxjOuDav4r"})
                                          |
                                      [:BY_ARTIST]
                                          v
                                  (:Artist {name:"Pitbull"})
                                          ^
                                      [:BY_ARTIST]
                                          |
                            (:Song {id:"4QNpBfC0zvjKqPJcyqBy9W"})
```

## Konsistensi lintas database

1. API menyimpan keadaan yang diinginkan (`liked`), revisi, dan `pending: true` dalam satu penulisan dokumen. MongoDB mengakui penulisan setelah jurnal lokal terisi. Permintaan suka berulang dengan nilai yang sama mempertahankan revisi.
2. Satu pekerja di dalam proses aplikasi membaca dokumen tertunda. Untuk suka, pekerja menjalankan `MERGE` pada relasi. Untuk batal suka, pekerja menghapus relasi jika ada.
3. Setelah transaksi graf selesai, pekerja menghapus tanda tertunda **hanya jika revisi masih sama**. Jika pengguna membatalkan suka selama sinkronisasi, revisi yang baru tetap masuk antrean.
4. Jika salah satu layanan terhenti di tengah proses, pekerja mencoba kembali. Perubahan cepat pada pasangan yang sama bisa digabung karena yang diperlukan adalah **status terakhir**. Sampel dan playlist tetap dapat diakses ketika hanya Neo4j yang berhenti.

MongoDB menangani penulisan satu dokumen secara atomik. Implementasi memanfaatkan sifat ini agar satu pembaruan juga mencatat pekerjaan sinkronisasi. [Dokumentasi MongoDB](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)

## Memeriksa kedua database

Cari lagu di **mongosh** (atau masukkan filter yang sama di Compass).

```javascript
use ruangnada
db.songs.find({keys: /^pitbull/}, {_id: 1, title: 1, artists: 1, genre: 1})
db.likes.findOne({_id: "pendengar-demo/2bJvI42r8EF3wxjOuDav4r"})
```

Setelah menyukai **Time of Our Lives**, jalankan di **Neo4j Browser**. Pilih tampilan Graph agar jalur hubungan terlihat.

```cypher
MATCH p = (:User {id:'pendengar-demo'})-[:LIKES]->(:Song {id:'2bJvI42r8EF3wxjOuDav4r'})
          -[:BY_ARTIST]->(:Artist {name:'Pitbull'})<-[:BY_ARTIST]-(:Song {id:'4QNpBfC0zvjKqPJcyqBy9W'})
RETURN p
```

Kueri Cypher yang dipakai aplikasi ada di [queries.py](app/queries.py). Penulisan dokumen, indeks dan pekerja sinkronisasi ada di [database.py](app/database.py). Endpoint integrasi, termasuk pencarian dan pengisian detail kandidat dari MongoDB, ada di [server.py](app/server.py).

## Mengulangi pengujian

Jalankan saat aplikasi siap, menggunakan Python 3 dari folder proyek.

```sh
python3 uji/integrasi.py
python3 uji/integrasi.py --pulihkan-graf
```

Perintah kedua juga menghentikan layanan Neo4j proyek, me-restart aplikasi selama graf offline, menyalakan graf kembali, dan memeriksa pemulihan. Pengujian menggunakan akun demo, memeriksa langsung dokumen MongoDB dan jumlah relasi Neo4j, kemudian mengembalikan status suka awal dan menghapus playlist uji yang dibuatnya. Jalankan saat akun demo bebas dari edit lain.

## Cakupan

Implementasi ini menguji pembagian tanggung jawab database dan pemulihan pembaruan suka pada 50 lagu, 64 artis, 47 album, dan enam kelompok genre. Genre merupakan klasifikasi luas yang ditetapkan khusus untuk demonstrasi, sedangkan judul, artis, album, tahun, durasi asli, dan ID Spotify diambil dari halaman Spotify. Pengukuran beban produksi, replikasi antarnode, sharding, autentikasi multipengguna, serta riwayat pemutaran berada di luar cakupan pengujian. Pekerja sinkronisasi dirancang untuk satu instans aplikasi seperti yang tercantum di Compose. Menambah instans memerlukan pengaturan kepemilikan pekerjaan atau kontrol versi pada sisi graf.

<details>
<summary>Asal sampul album</summary>

Keempat sampul dibuat dengan ImageGen bawaan sebagai satu [berkas sampul lokal](app/static/sampul.jpg). Prompt yang digunakan tercantum di bawah.

> Design one square digital album-art sprite atlas, a strict 2 by 2 grid of four equally sized full-bleed square photographs, no gutters or margins, edges meet exactly at the centerlines. Four anonymous original contemporary Indonesian music releases for a clean premium music library. TOP LEFT: dreamy fine-grain 35mm photograph of a cool mist-blue Indonesian volcanic mountain in early morning, glowing salmon orange rising sun and apricot overcast sky, strong graphic dark mountain silhouette and dreamy halation. TOP RIGHT: poetic defocused long-exposure beach at lavender dusk, deep magenta indigo water, slender crescent of warm evening light across the horizon. BOTTOM LEFT: kinetic electronic Jakarta night city photograph shot from a moving train, red-orange vertical light columns, blue-black blurred architecture with high contrast. BOTTOM RIGHT: minimal ambient still life of a glossy pale glass sphere on saturated cobalt blue and ice-blue background, intriguing caustic shadow. For all cells: sophisticated real photographic art direction, individual compositions bold at thumbnail size, calm visual structures, no people, absolutely no typography, numbers, branding, frames, or white lines. Final format is one production texture atlas.

</details>

