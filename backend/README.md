# Destek Takip — Backend

FastAPI, SQLAlchemy, Alembic ve Microsoft SQL Server tabanlı V2 backend'i.

## Gereksinimler

- Python 3.11 veya üzeri
- Microsoft ODBC Driver 18 for SQL Server
- Erişilebilir bir Microsoft SQL Server veritabanı

## Yerel kurulum (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

`.env` içindeki MSSQL değerlerini kuruma göre düzenleyin. Parola ve secret değerlerini repoya eklemeyin.

Yerel bir SQL Server Express named instance kullanılıyorsa sunucu adı ters eğik çizgiyle yazılır
ve port eklenmez. Örnek:

```dotenv
APP_DATABASE_SERVER=.\SQLEXPRESS02
APP_DATABASE_NAME=DestekTakip
APP_DATABASE_TRUSTED_CONNECTION=true
APP_DATABASE_ENCRYPT=true
APP_DATABASE_TRUST_SERVER_CERTIFICATE=true
```

`APP_DATABASE_TRUST_SERVER_CERTIFICATE=true` yalnızca yerel, güvenilen geliştirme instance'ının
self-signed sertifikası için uygundur. Üretimde geçerli sunucu sertifikasıyla `false` kullanılmalıdır.

Kimlik doğrulama için özellikle şu değerleri ortama göre değiştirin:

```dotenv
APP_ALLOWED_EMAIL_DOMAINS=["example.com"]
APP_SESSION_SECRET=en-az-32-karakterlik-benzersiz-rastgele-bir-deger
APP_UPLOAD_ROOT=D:/DestekTakip/uploads
```

`APP_SESSION_COOKIE_SECURE` tanımlanmazsa production ortamında otomatik olarak `true`, diğer
ortamlarda `false` olur.

## Migration

```powershell
alembic upgrade head
```

Migration'lar şu nesneleri oluşturur:

- `ticket_number_seq`
- `users`
- `tickets`
- `attachments`
- `notifications`
- `ticket_ratings`
- `deleted_accounts`
- `audit_events`
- İlişkili PK, FK, unique/check constraint ve indeksler

## Çalıştırma

```powershell
uvicorn app.main:app --reload
```

Canlılık endpoint'i:

```text
GET http://127.0.0.1:8000/api/health/live
```

Veritabanı hazırlık endpoint'i:

```text
GET http://127.0.0.1:8000/api/health/ready
```

## Merkezi loglama ve sistem izleme

Uygulama, güvenli bağlam alanlarıyla satır bazlı JSON log üretir. Dosya boyuta göre döner; dosya,
boyut ve saklanacak eski dosya sayısı `.env` üzerinden belirlenir:

```dotenv
APP_LOG_LEVEL=INFO
APP_LOG_FILE=data/logs/application.jsonl
APP_LOG_MAX_BYTES=10485760
APP_LOG_BACKUP_COUNT=5
```

Loglara parola, cookie, token, bağlantı parolası, istek gövdesi veya yüklenen dosya içeriği
yazılmaz. IT ve ADMIN kullanıcıları web arayüzündeki **Sistem İzleme** ekranından genel sağlık,
MSSQL hazırlığı, upload alanı, çalışma süresi ve son güvenli olayları takip edebilir.

| Metot | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/api/it/system/overview` | Uygulama, MSSQL, upload ve log özetini döndürür |
| `GET` | `/api/it/system/logs` | Seviye ve limit filtreli merkezi logları döndürür |

Bu endpoint'ler `IT` ve `ADMIN` rollerine açıktır. İleride kurumun SIEM/Seq/ELK altyapısı devreye
alındığında JSON log dosyaları bir ajanla merkezi sisteme taşınabilir; uygulama kodu ve olay
şeması değişmeden kalır.

## Kimlik doğrulama

Oturum akışı imzalı, `HttpOnly` session cookie'si kullanır. Değişiklik yapan oturumlu
isteklerde, okunabilir CSRF cookie'sinin değeri `X-CSRF-Token` başlığıyla da gönderilmelidir.

| Metot | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/api/auth/register` | İzin verilen e-postayla `USER` hesabı oluşturur |
| `POST` | `/api/auth/login` | Oturum açar |
| `POST` | `/api/auth/logout` | Oturumu kapatır; CSRF başlığı gerektirir |
| `GET` | `/api/auth/me` | Oturumdaki kullanıcıyı döndürür |
| `GET` | `/api/users/me` | Kullanıcı profilini döndürür |
| `PATCH` | `/api/users/me` | Profili günceller; CSRF başlığı gerektirir |
| `POST` | `/api/users/me/password` | Parolayı değiştirir ve geçici parola zorunluluğunu kaldırır |

Kayıt endpoint'i istemciden rol kabul etmez; tüm yeni hesaplar `USER` olarak oluşturulur.
İlk `ADMIN` hesabı yalnızca sunucu terminalinden oluşturulur:

```powershell
python -m app.cli.create_initial_admin `
  --email admin@example.com `
  --first-name Sistem `
  --last-name Yöneticisi
```

Sonraki IT hesapları ADMIN panelinden geçici parolayla oluşturulur. Eski kurulum ve acil durum
senaryoları için ilk IT komutu da korunmuştur:

```powershell
python -m app.cli.create_initial_it `
  --email it.manager@example.com `
  --first-name Bilgi `
  --last-name İşlem
```

Komut şifreyi terminalde gizli olarak iki kez ister.

## Ticket API'si

Kullanıcı endpoint'leri yalnızca oturum sahibinin ticket'larını döndürür. İstemciden `user_id`,
`priority`, atama veya çözüm alanları kabul edilmez.

| Metot | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/api/tickets` | Konu ve açıklamayla ticket oluşturur |
| `GET` | `/api/tickets` | Kullanıcının ticket'larını sayfalı listeler |
| `GET` | `/api/tickets/{id}` | Kullanıcının kendi ticket detayını döndürür |
| `PATCH` | `/api/tickets/{id}` | Çözülmemiş kendi ticket'ını günceller |

| `DELETE` | `/api/tickets/{id}` | Çözülmemiş kendi ticket'ını nedenle geri dönüşüm kutusuna taşır |
| `GET/PUT` | `/api/tickets/{id}/rating` | Çözülmüş talebin IT hizmet puanını okur veya 7 gün içinde kaydeder |
| `GET` | `/api/it/tickets` | IT için tüm ticket'ları arar ve filtreler |
| `GET` | `/api/it/tickets/{id}` | IT ticket detayını döndürür |
| `PATCH` | `/api/it/tickets/{id}/priority` | Öncelik belirler |
| `POST` | `/api/it/tickets/{id}/assign-self` | Atanmamış ticket'ı oturumdaki IT'ye atar |
| `POST` | `/api/it/tickets/{id}/resolve` | Atanmış ticket'ı çözüldü/çözülemedi sonucu ve açıklamasıyla kapatır |

### 0.5 operasyon geliştirmeleri

- `GET /api/tickets`: çalışan için `search`, `status`, `priority` ve tarih aralığı filtreleri
- `GET /api/it/tickets`: açıklama/çözüm/kullanıcı araması; durum, öncelik, departman,
  sorumlu, etiket ve tarih aralığı filtreleri
- `GET /api/it/tickets/filter-options`: filtre seçim verileri
- `GET /api/{it|admin}/tickets/{id}/history`: ticket işlem geçmişi
- `POST/DELETE /api/it/tickets/{id}/watch`: ticket takipçi yönetimi
- `POST/DELETE /api/it/tickets/{id}/tags/{tag_id}`: ticket etiket yönetimi
- `GET/POST /api/it/tags`: etiket listeleme ve oluşturma
- `GET /api/it/reports/dashboard`: BT operasyon dashboard'u
- `GET /api/it/reports/summary`: gelişmiş trend ve performans özeti; IT ve ADMIN erişimi
- `GET/POST/PATCH/DELETE /api/admin/canned-responses`: hazır yanıt yönetimi

Bu özelliklerin MSSQL nesneleri `20260825_0005_ticket_operations.py` migration'ıyla eklenir.

Liste endpoint'lerinde `page` varsayılan olarak `1`, `page_size` varsayılan olarak `20` ve en
fazla `100` olabilir. IT listesinde `view=all|unassigned|mine|resolved` filtresi ile `search`
parametresi kullanılabilir. Arama; ticket numarası, kullanıcı adı/e-postası, departman ve konu
alanlarını kapsar.

## ADMIN ve geri dönüşüm API'leri

| Metot | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/api/admin/dashboard` | Yönetim metriklerini döndürür |
| `GET/POST` | `/api/admin/users`, `/api/admin/users/it` | Kullanıcıları listeler ve IT hesabı oluşturur |
| `PATCH/POST` | `/api/admin/users/{id}/*` | Profil, durum ve geçici parola yönetimini yapar |
| `GET/DELETE` | `/api/admin/tickets` | Aktif/silinmiş talepleri listeler ve soft-delete uygular |
| `POST` | `/api/admin/tickets/{id}/restore` | Silinmiş talebi geri yükler |
| `GET` | `/api/admin/audit-events` | Kritik işlem olaylarını sayfalı döndürür |

Silme fiziksel değildir; silen kullanıcı, UTC zamanı ve neden saklanır. Normal ticket listeleri,
ek erişimi ve raporlar silinmiş kayıtları dışarıda bırakır. İş geçmişi olmayan kullanıcı hesapları
kalıcı silinebilir; silinen e-posta adresinin geri kayıt edilmesini önlemek için yalnızca geri
döndürülemez bir güvenlik parmak izi saklanır.

## Dosya ekleri

Dosyalar public klasör dışında, `APP_UPLOAD_ROOT` altında rastgele UUID adlarıyla tutulur.
İstemcinin dosya adı hiçbir zaman disk yolu olarak kullanılmaz. Varsayılan sınırlar dosya başına
10 MB ve ticket başına 5 ektir.

| Metot | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/api/tickets/{id}/attachments` | `multipart/form-data` ile PNG, JPG/JPEG veya PDF yükler |
| `GET` | `/api/tickets/{id}/attachments/{attachment_id}` | Yetki kontrolünden sonra eki indirir |
| `DELETE` | `/api/tickets/{id}/attachments/{attachment_id}` | Sahibi olduğu çözülmemiş ticket ekini kaldırır |

Dosya yüklemede uzantı, istemcinin bildirdiği MIME türü ve gerçek dosya imzası birlikte kontrol
edilir. Çözülmüş ticket ekleri salt okunurdur. IT ve ADMIN kullanıcıları tüm ticket eklerini indirebilir,
ancak kullanıcı eklerini silemez.

## Bildirim ve SMTP

```dotenv
APP_EMAIL_DELIVERY_ENABLED=true
APP_SMTP_HOST=smtp.example.com
APP_SMTP_PORT=587
APP_SMTP_USERNAME=ticket-service
APP_SMTP_PASSWORD=secret-degeri
APP_SMTP_USE_TLS=true
APP_MAIL_FROM=tickets@example.com
APP_IT_NOTIFICATION_RECIPIENTS=["it@example.com"]
```

`APP_EMAIL_DELIVERY_ENABLED=false` ise SMTP'den bağımsız sistem içi bildirimler çalışmaya devam
eder ve e-posta teslim durumu `SKIPPED` olur. SMTP hatası
ticket oluşturma veya çözme işlemini geri almaz; bildirim kaydında `FAILED` olarak izlenir.
Yeni ticket için aktif IT hesaplarına, çözüm sırasında ticket sahibine sistem içi bildirim
oluşturulur.

`APP_IT_NOTIFICATION_RECIPIENTS` tanımlanırsa listedeki adreslerin aktif IT hesaplarının e-posta
adresleriyle eşleşmesi gerekir. Liste boş bırakılırsa tüm aktif IT hesapları e-posta alır.

| Metot | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/api/notifications` | Oturum sahibinin bildirimlerini sayfalı listeler |
| `PATCH` | `/api/notifications/{id}/read` | Oturum sahibinin bildirimini okundu işaretler |

## Public demo sıfırlama

İnternete açık ortak demo ortamını korunan USER, IT ve ADMIN hesapları ile dört örnek talebe
döndürmek için aşağıdaki yönetim komutu kullanılır:

```powershell
python -m app.cli.reset_demo --confirm RESET-DEMO
```

Komut yalnızca `APP_DEMO_MODE=true` olduğunda çalışır. Korunmayan kullanıcıları ve operasyon
verilerini kalıcı olarak siler, demo profilleri ile parolalarını environment değerlerinden
yeniler ve `APP_UPLOAD_ROOT` içeriğini temizler. Bu nedenle yalnızca ayrı bir demo veritabanı
ve dosya alanında, zamanlanmış yönetim işi olarak çalıştırılmalıdır.

## Raporlama

Rapor endpoint'leri `IT` ve `ADMIN` rollerine açıktır. `period=today|week|month|custom` parametresi
kullanılır; `custom` seçildiğinde `date_from` ve `date_to` değerleri `YYYY-MM-DD` biçiminde ve
birlikte gönderilmelidir. Dönem sınırları İstanbul saat dilimine göre hesaplanır.

| Metot | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/api/it/reports/summary` | Toplam, açık/çözülen, ortalama çözüm süresi ve departman dağılımını döndürür |
| `GET` | `/api/it/reports/export.xlsx` | Aynı dönemi özet ve ticket detay sayfalarıyla, İstanbul saatiyle Excel olarak indirir |

Excel çıktısında hücre formülü ve URL algılama kapalıdır; kullanıcı girdileri çalıştırılabilir
formüle dönüşmez.

## Test

```powershell
python -m pytest
python -m ruff check app tests
```

## Üretim ön kontrolü

`APP_ENVIRONMENT=production` ayarlarıyla çalıştırıldığında aşağıdaki komut güvenli production
yapılandırmasını, upload klasörüne yazma iznini, MSSQL bağlantısını ve migration seviyesini
doğrular. Herhangi bir kontrol başarısızsa backend süreci başlatılmamalıdır.

```powershell
python -m app.cli.preflight
```

Tam Windows/IIS yayın sırası ve kabul listesi için `deployment/README.md` belgesine bakın.

## Güvenlik notları

- MSSQL bağlantı bilgileri yalnızca environment üzerinden alınır.
- Varsayılan bağlantı ODBC Driver 18, şifreleme ve sertifika doğrulaması kullanır.
- `APP_DATABASE_TRUST_SERVER_CERTIFICATE=true` yalnızca kontrollü geliştirme ortamlarında kullanılmalıdır.
- Şifreler rastgele salt ile `scrypt` kullanılarak özetlenir; düz metin tutulmaz.
- Oturum cookie'si HMAC-SHA256 ile imzalanır ve varsayılan olarak 8 saat geçerlidir.
- Oturumlu veri değiştirme istekleri CSRF cookie/header eşleşmesi ve izinli origin denetiminden geçer.
- Kullanıcıya ait olmayan kaynaklar, kaynak varlığını sızdırmamak için `404` ile gizlenir.
- Dosya indirme yalnızca yetkilendirmeli API üzerinden yapılır; storage key API yanıtında dönmez.
- SMTP parolası ve teslim hatası kullanıcı API yanıtlarında gösterilmez.
- Uygulama loglarına bağlantı parolası, cookie, token veya kullanıcı dosya içeriği yazılmamalıdır.
