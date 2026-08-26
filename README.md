# Destek Takip

Teknik destek taleplerini oluşturmak, IT ekibine atamak, çözüm sürecini izlemek ve raporlamak
için geliştirilmiş rol tabanlı web uygulaması. React arayüzü, FastAPI REST API'si ve Microsoft
SQL Server veri katmanı birlikte çalışır.

## Proje yapısı

- `backend/`: FastAPI, SQLAlchemy, Alembic ve Microsoft SQL Server backend'i
- `frontend/`: React ve Vite web arayüzü
- `deployment/`: Windows/IIS yayın, ön kontrol ve kabul araçları

İlk analiz belgeleri, çalışma verileri ve yerel ortam dosyaları public kaynak paketine dahil
edilmez.

## Hızlı başlatma

Çalışan MSSQL dâhil tüm sistemi en hızlı biçimde Docker Compose ile açabilirsiniz:

```powershell
docker compose --env-file .env.compose.example up --build -d
```

Uygulama hazır olduğunda <http://localhost:8080> adresinde çalışır. Ayrıntılı başlangıç,
demo hesap, SSMS ve sorun giderme adımları için [container rehberini](deployment/CONTAINERS.md)
kullanın.

Container kullanmadan geliştirmek için önce [backend kurulumunu](backend/README.md), ardından
[frontend kurulumunu](frontend/README.md) tamamlayın. Uygulama çalışma ortamında MSSQL kullanır;
makineye özel bağlantı ve secret değerleri yalnızca Git tarafından izlenmeyen `backend/.env`
dosyasında tutulur.

Üretim ortamında migration çalıştırılmalı, ilk ADMIN hesabı CLI ile açılmalı ve secret, MSSQL,
upload, log, SMTP, HTTPS/cookie ile CORS ayarları yayın ortamına göre tanımlanmalıdır. IT ve
ADMIN rolleri web arayüzündeki **Sistem İzleme** ekranından MSSQL hazırlığını, dosya alanını
ve dönen merkezi JSON uygulama loglarını izleyebilir.

Güncel işlevler:

- ADMIN panelinden IT hesabı açma, geçici parola ve hesap durumu yönetimi
- Kullanıcı ve yönetici için neden zorunlu, geri yüklenebilir talep silme
- Kritik işlemler için kalıcı denetim olayları
- Çalışan ve BT havuzlarında sunucu taraflı arama ve ayrıntılı filtreler
- BT için ayrı "Benim Ticketlarım" görünümü, Liste/Kanban geçişi ve son güncelleme bilgisi
- Ticket işlem geçmişi, etiketler, takipçiler, çakışma görünürlüğü ve hazır yanıtlar
- Operasyon dashboard'u; trend, öncelik, departman ve BT çözüm performansı raporları
- Admin için ticket ayrıntısı, hazır yanıt yönetimi ve gelişmiş rapor erişimi

Windows/IIS üretim adımları, ön kontrol ve kabul senaryoları için
[deployment yayın rehberini](deployment/README.md) kullanın.

## Ortam seçenekleri

- `APP_ALLOWED_EMAIL_DOMAINS`: kullanılabilecek e-posta alan adları
- `APP_PUBLIC_REGISTRATION_ENABLED`: public kayıt endpoint'ini açar veya kapatır
- `APP_DEMO_MODE`: ortak demo hesaplarının korunmasını etkinleştirir
- `APP_DEMO_PROTECTED_EMAILS`: değiştirilemeyecek demo hesapları
- `APP_EMAIL_DELIVERY_ENABLED`: sistem içi bildirimlerden bağımsız SMTP teslim anahtarı
- `VITE_APP_NAME`: arayüzde gösterilecek ürün adı
- `VITE_PUBLIC_REGISTRATION_ENABLED`: kayıt bağlantısı ve ekranının build ayarı

## Doğrulama

```powershell
cd backend
python -m pytest
python -m ruff check app tests

cd ..\frontend
npm test
npm run lint
npm run build
```
