# Yerel container ortamı

Bu ortam; Nginx web katmanı, FastAPI backend'i ve Microsoft SQL Server 2022'yi tek
bir Docker Compose projesinde çalıştırır. Tarayıcı yalnızca Nginx'e bağlanır; `/api`
istekleri aynı origin üzerinden backend'e iletilir. Backend ve veritabanı dış ağa
açılmaz. MSSQL'in host portu yalnızca yerel SSMS kontrolleri için `127.0.0.1` üzerinde
yayınlanır.

## Gereksinimler

- Docker Desktop (Linux container modu)
- Docker Compose
- En az 4 GB kullanılabilir Docker belleği

## Başlatma

Proje kökünde aşağıdaki komutları çalıştırın:

```powershell
docker compose --env-file .env.compose.example config
docker compose --env-file .env.compose.example up --build -d
docker compose --env-file .env.compose.example ps
```

Uygulama: <http://localhost:8080>

Demo hesapları:

| Rol | E-posta |
| --- | --- |
| Kullanıcı | `demo.user@example.com` |
| IT çalışanı | `demo.it@example.com` |
| Yönetici | `demo.admin@example.com` |

Üç hesap da `.env.compose.example` içindeki `DEMO_ACCOUNT_PASSWORD` değerini kullanır.
Bu dosyadaki değerler yalnızca yerel geliştirme içindir; internete açık bir ortamda
kullanılmamalıdır.

## İzleme ve sorun giderme

```powershell
docker compose --env-file .env.compose.example ps
docker compose --env-file .env.compose.example logs -f backend frontend
docker compose --env-file .env.compose.example logs db migrate demo-seed
```

Hazırlık kontrolleri:

```powershell
Invoke-WebRequest http://localhost:8080/healthz
Invoke-WebRequest http://localhost:8080/api/health/live
Invoke-WebRequest http://localhost:8080/api/health/ready
```

SSMS bağlantısı için sunucu adı `localhost,14330`, kimlik doğrulama `SQL Server
Authentication`, kullanıcı `sa` ve parola `.env.compose.example` içindeki
`MSSQL_SA_PASSWORD` değeridir. Yerel sertifika kullanıldığı için **Trust server
certificate** seçili olmalıdır.

## Kontrollü demo sıfırlama

Demo hesaplarını başlangıç parolasına döndürmek; sonradan oluşan kullanıcıları, talepleri,
bildirimleri ve dosya eklerini temizlemek; dört örnek talebi yeniden kurmak için:

```powershell
docker compose --env-file .env.compose.example --profile tools run --rm demo-reset
```

Komut yalnızca `APP_DEMO_MODE=true` olduğunda ve açık `RESET-DEMO` onayıyla çalışır. Veritabanı
ilişkilerini güvenli sırada temizler, yalnızca korunan üç demo hesabını saklar ve upload
volume'ünü başlangıç durumuna döndürür. Bu işlem demo verileri için geri alınamaz.

## Durdurma

Container'ları durdurup verileri korumak için:

```powershell
docker compose --env-file .env.compose.example down
```

`docker compose down -v` komutu MSSQL veritabanı, yüklenen dosyalar ve loglar dâhil
tüm kalıcı volume'leri siler. Yalnızca tamamen temiz bir demo ortamı istendiğinde
ve veri kaybı kabul edildiğinde kullanılmalıdır.
