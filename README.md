# LinkedIn Job Hunter

LinkedIn'de **son 24 saatte yayınlanan** ilanları senin anahtar kelimelerine göre
tarar, daha önce görmediklerini bulur ve sana **e-posta** gönderir.

LinkedIn'de "en yeniden en eskiye" düzgün bir sıralama olmadığı için, iş şu:
her 10 dakikada bir arka planda arama yapılır, yeni çıkan ilanlar tespit edilir
ve sadece **daha önce bildirilmemiş** olanlar sana gelir.

- En fazla **10 anahtar kelime** (ör. `finans`, `FP&A`, `IFRS`)
- **Konum** seçilebilir (ör. `İstanbul, Türkiye`) — boş bırakırsan her yer
- **GitHub Actions** üzerinde çalışır: bilgisayarın kapalıyken de tarar, ücretsiz
- Aynı ilan iki kez gönderilmez
- Birden fazla arama tanımlayıp **farklı kişilere farklı ilanlar** gönderebilirsin

---

## Kurulum (tek seferlik, ~10 dakika)

### 1. Gmail uygulama şifresi oluştur

E-postayı gönderecek hesabın normal şifresi işe yaramaz; Google "uygulama şifresi"
istiyor.

1. Google hesabında **iki adımlı doğrulamayı** aç (zorunlu):
   <https://myaccount.google.com/signinoptions/two-step-verification>
2. <https://myaccount.google.com/apppasswords> adresine git, bir isim yaz
   (ör. `ilan-takip`), oluştur.
3. Çıkan **16 haneli şifreyi** kopyala. Bir daha gösterilmez.

> Gmail kullanmıyorsan sağlayıcının SMTP bilgilerini `SMTP_HOST` / `SMTP_PORT`
> secret'larıyla verebilirsin. Outlook: `smtp.office365.com` / `587`.

### 2. Secret'ları GitHub'a ekle

Repo sayfasında **Settings → Secrets and variables → Actions → New repository secret**
yolunu izleyip şunları ekle:

| Secret adı      | Değer                                          | Zorunlu |
|-----------------|------------------------------------------------|---------|
| `SMTP_USERNAME` | Gönderen Gmail adresin                         | Evet    |
| `SMTP_PASSWORD` | Yukarıda aldığın 16 haneli uygulama şifresi    | Evet    |
| `SMTP_HOST`     | `smtp.gmail.com` (Gmail dışıysa değiştir)      | Hayır   |
| `SMTP_PORT`     | `587`                                           | Hayır   |
| `SMTP_FROM`     | Farklı bir "gönderen" adresi istiyorsan        | Hayır   |
| `EMAIL_RECIPIENTS` | Bildirimin gideceği adres(ler), virgülle ayrılmış | Hayır* |
| `NTFY_TOPIC`    | Sadece ntfy'yi açtıysan                        | Hayır   |

\* **Bu repo herkese açık (public).** `config.yaml` içine yazdığın her şeyi
herkes görebilir — e-posta adresin dahil. Adresini repoda göstermek istemiyorsan
`config.yaml` içindeki `recipients` listesini boş bırak ve adres(ler)ini
`EMAIL_RECIPIENTS` secret'ı olarak ver:
`senin-adresin@gmail.com,arkadasin@gmail.com`. Secret'lar repoda görünmez.

> Repoyu **private** yapmayı da düşünebilirsin, ama dikkat: private repolarda
> GitHub Actions ayda 2000 dakika ücretsizdir ve 10 dakikalık tarama bu sınırı
> aşar. Public repoda Actions dakikası sınırsızdır. Bu yüzden önerim: repo public
> kalsın, kişisel bilgi `EMAIL_RECIPIENTS` secret'ında dursun.

Şifre asla `config.yaml` içine yazılmaz; secret'lar repoda görünmez.

### 3. `config.yaml` dosyasını düzenle

En az şunları değiştir:

```yaml
searches:
  - name: "Finans / FP&A"
    keywords: [finans, "FP&A", IFRS]     # en fazla 10 tane
    location: "İstanbul, Türkiye"
    match_mode: any                       # any = herhangi biri, all = hepsi
    exclude: [stajyer, intern]            # bu kelimeler geçerse gönderme

notifications:
  email:
    recipients: []      # adresini EMAIL_RECIPIENTS secret'ında tut (yukarı bak)
```

### 4. Actions'ı aç ve test et

1. Repo'da **Actions** sekmesine gir, uyarı çıkarsa workflow'ları etkinleştir.
2. **LinkedIn ilan taraması** workflow'unu seç → **Run workflow**.
   İlk denemede `dry_run` kutusunu işaretlersen e-posta gitmez, sadece bulunan
   ilanlar log'a yazılır — ayarları kontrol etmenin en kolay yolu.
3. Log'da ilanları görüyorsan `dry_run` olmadan bir kez daha çalıştır; e-posta
   gelmeli.

Bundan sonra **her 10 dakikada bir** kendi kendine çalışır.

> **Önemli:** GitHub, zamanlanmış (cron) çalıştırmayı **sadece deponun varsayılan
> (default) branch'inde** yapar. Bu kod bir feature branch'te duruyorsa, otomatik
> tarama başlamaz — kodu varsayılan branch'e (`main`) birleştir.
> Ayrıca 60 gün boyunca repoda hiç aktivite olmazsa GitHub zamanlayıcıyı
> durdurur; kayıt dosyası her taramada güncellendiği için normalde bu olmaz.

---

## Kendi bilgisayarında çalıştırmak (opsiyonel)

```bash
pip install -r requirements.txt

export SMTP_HOST=smtp.gmail.com
export SMTP_USERNAME=senin-adresin@gmail.com
export SMTP_PASSWORD=uygulama-sifresi
export EMAIL_RECIPIENTS=senin-adresin@gmail.com

python -m job_hunter --config config.yaml --dry-run   # deneme
python -m job_hunter --config config.yaml             # gerçek gönderim
```

---

## Arkadaşlarına vermek

İki yolu var:

**A) Aynı kurulumdan herkese gönder (en kolay).**
Arkadaşın hiçbir şey yapmaz. Sen onun için ayrı bir arama tanımlarsın; kendi
anahtar kelimelerini ve konumunu alır, e-posta doğrudan ona gider.

Adresini `config.yaml`'a yazma — repo herkese açıksa adres de açık olur. Bunun
yerine adresi bir secret olarak ekle (ör. `AYSE_EMAIL`) ve adını
`recipients_secret` alanına yaz:

```yaml
searches:
  - name: "Benim aramam"
    keywords: [finans, "FP&A", IFRS]
    location: "İstanbul, Türkiye"
    # kendi recipients'ı yok → EMAIL_RECIPIENTS secret'ındaki adres(ler)e gider

  - name: "Ayşe – denetim"
    keywords: ["internal audit", denetim]
    location: "Ankara, Türkiye"
    recipients_secret: AYSE_EMAIL    # sadece bu adrese gider
    enabled: true
```

Dağıtım kuralı: bir aramanın kendi alıcısı varsa sonuçlar **yalnızca** ona
gider; yoksa `notifications.email.recipients` / `EMAIL_RECIPIENTS`'taki genel
adreslere düşer. Yani kimse başkasının ilanlarını almaz ve kimse diğerinin
adresini görmez.

**Birini durdurmak** (iş buldu, ara vermek istiyor): aramayı silmene gerek yok,
`enabled: false` yeter. Kelimeleri yerinde kalır, tekrar başlarken `true`
yaparsın.

**B) Repoyu fork'lasınlar.**
Arkadaşın repoyu fork'lar, kendi Gmail uygulama şifresini kendi secret'ı olarak
ekler, `config.yaml`'ı kendine göre düzenler. Tamamen bağımsız çalışır — senin
Gmail hesabını ve kotanı kullanmaz. Birden fazla kişi olacaksa bu yol daha temiz.

---

## Bildirimi başka bir kanala almak

Kod, bildirim kanallarını ayrı tutuyor; `config.yaml` üzerinden açılıp kapanır.

**ntfy (telefona anlık push)** hazır ama **varsayılan olarak kapalı**. Açmadan
önce bilmen gereken: `ntfy.sh` üzerinde konu (topic) adları şifresizdir —
konu adını bilen veya tahmin eden herkes bildirimlerini okuyabilir, hatta o
konuya sahte bildirim gönderebilir. Konu adı fiilen şifren demektir. Açacaksan
tahmin edilemeyecek bir isim seç (ör. `ilanlar-8f3k92xq`) veya ntfy'yi kendi
sunucunda barındır.

```yaml
notifications:
  ntfy:
    enabled: true
    topic: "ilanlar-8f3k92xq"
```

Discord/Slack webhook gibi kanallar da aynı yapıya kolayca eklenebilir:
`job_hunter/notifiers/` altına yeni bir dosya, `runner.notify` içine bir çağrı.

---

## Neden Vercel değil?

- Vercel'in ücretsiz planında **cron günde sadece 1 kez** çalışır; 10 dakikada
  bir tarama oradan mümkün değil.
- Vercel fonksiyonları durumsuzdur — "bu ilanı zaten gönderdim" kaydı için ayrıca
  bir veritabanı bağlamak gerekir.
- Ortada bir web sitesi yok; bu, arka planda çalışan bir görev.

GitHub Actions bu üç sorunun üçünü de çözüyor: sık cron, repoya yazılabilen kalıcı
kayıt, sıfır ek servis.

---

## Bilinmesi gerekenler

- **LinkedIn'in resmî bir iş ilanı API'si yok.** Bu araç, LinkedIn'in giriş
  yapmadan görünen arama sayfasını okur. Kişisel ölçekte ve düşük istek
  sıklığında çalışır; tarama sıklığını çok artırırsan LinkedIn istekleri geçici
  olarak sınırlayabilir. Varsayılan ayar 10 dakikada bir tarama ve istekler arası
  3 saniye bekleme. 3 anahtar kelimeyle bu, saatte ~18 istek eder — düşük bir
  sayı, sorun çıkarması beklenmez. Yine de LinkedIn 429 döndürürse tarama o tur
  için durur ve bir sonraki turda kaldığı yerden devam eder, ilan kaçmaz.
- **Cron aralığını daha da kısaltmak işe yaramaz.** GitHub'ın zamanlayıcısı
  garantili değildir: yoğun saatlerde çalışmalar gecikir, hatta bazı turlar
  atlanabilir. `*/5` yazsan bile pratikte 10-15 dakikada bir çalışır. `*/10`
  bu yüzden makul üst sınır.
- LinkedIn sayfa yapısını değiştirirse tarama boş dönebilir. Bu durumda log'a
  `hiç ilan kartı ayrıştırılamadı` uyarısı düşer — sessizce sus pus olmaz.
- Eşleşme yalnızca **ilan başlığı** üzerinden yapılır; ilan metninin tamamı
  okunmaz (bu, ilan başına ayrı bir istek demek olurdu). Şirket adına bakılmaz:
  aksi halde adında "Finans" geçen bir bankanın her ilanı eşleşirdi.
- Anahtar kelime, kelimenin başından eşleşir: `finans` yazınca "Finansal
  Raporlama" da gelir, ama alakasız bir kelimenin ortasındaki harf dizisi
  eşleşmez. Büyük/küçük harf ve Türkçe karakter farkı önemsizdir
  (`İSTANBUL` = `istanbul`).
- E-posta gönderilemezse ilanlar "görüldü" olarak işaretlenmez; bir sonraki
  tarama aynı ilanları tekrar dener, kaçmaz.

## Proje yapısı

```
job_hunter/
  cli.py          komut satırı girişi
  config.py       config.yaml okuma ve doğrulama (5 kelime sınırı burada)
  linkedin.py     LinkedIn arama isteği ve ilan kartlarının ayrıştırılması
  matching.py     anahtar kelime eşleştirme (any / all / exclude)
  storage.py      daha önce bildirilen ilanların kaydı
  runner.py       tarama → eşleştirme → bildirim akışı
  notifiers/      e-posta, ntfy ve e-posta içeriğinin şablonu
.github/workflows/
  job-hunt.yml    her 30 dakikada bir çalışan tarama
  tests.yml       testler
config.yaml       senin ayarların
state/            görülen ilanların kaydı (otomatik güncellenir)
```

## Testler

```bash
pip install -r requirements-dev.txt
pytest -q
```
