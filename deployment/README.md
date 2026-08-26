# Windows/IIS Üretim Yayın Rehberi

Bu paket Docker'sız Windows/IIS yayını içindir. IIS statik React
dosyalarını sunar ve `/api` isteklerini yalnızca `127.0.0.1:8000` üzerinde çalışan FastAPI
sürecine iletir. Dışarıya tek HTTPS origin açılır.

## Kurumdan alınacak değerler

- Uygulama DNS adı ve geçerli TLS sertifikası
- MSSQL sunucu/veritabanı ve servis hesabı yetkileri
- İzin verilecek e-posta alan adları
- SMTP host, hesap, parola, gönderici ve IT alıcıları
- Mutlak upload klasörü, NTFS servis hesabı ve yedekleme politikası
- Mutlak dönen JSON log klasörü, saklama süresi ve izleme sorumlusu
- İlk ADMIN hesabı bilgileri

Bu bilgiler olmadan gerçek üretim kurulumu ve kabul testi tamamlanmış sayılmaz.

## Sunucu önkoşulları

- Python 3.11+ x64
- Node.js 22+ yalnızca build makinesinde
- Microsoft ODBC Driver 18 for SQL Server
- IIS, URL Rewrite Module ve Application Request Routing (ARR)
- IIS'te proxy özelliği etkin, HTTPS binding zorunlu
- Backend ve upload klasörüne erişen ayrı, en az yetkili Windows servis hesabı

## Kurulum sırası

1. `backend/.env.production.example` dosyasını `backend/.env` olarak kopyalayın ve tüm örnek
   değerleri kurum değerleriyle değiştirin. `.env` dosyasına yalnızca servis hesabı ile
   yöneticilerin okuma izni olmalıdır.
2. Upload ve log klasörlerini oluşturun; servis hesabına değişiklik, diğer hesaplara gereksiz
   erişim vermeyin. Upload klasörünü uygulama veritabanıyla tutarlı yedekleme planına ekleyin.
3. Backend ortamını hazırlayın:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install .
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m app.cli.preflight
   ```

4. İlk ADMIN hesabını backend README'sindeki CLI komutuyla oluşturun; sonraki IT hesaplarını
   web yönetim panelinden geçici parolayla açın.
5. Frontend'i güvenilir build makinesinde `npm ci` ve `npm run build` ile derleyin. `dist/`
   içeriğini IIS site köküne kopyalayın. `public/web.config` build sırasında `dist/web.config`
   olarak eklenir.
6. `Start-Backend.ps1` komutunu servis yöneticisinin çalıştıracağı komut olarak kullanın. Süreci
   LocalSystem yerine kısıtlı servis hesabıyla çalıştırın ve otomatik yeniden başlatma tanımlayın.
7. IIS HTTPS binding'ini ve ARR proxy özelliğini doğrulayın; port 8000'i dış ağ güvenlik
   duvarına açmayın.
8. `Smoke-Test.ps1 -BaseUrl https://support.example.com` çalıştırın, ardından
   `ACCEPTANCE-CHECKLIST.md` listesini gerçek USER, IT ve ADMIN test hesaplarıyla tamamlayın.

## Yayın adayı paketi

Kaynak ağaçtan test edilmiş, secret içermeyen ve SHA-256 manifestli ZIP üretmek için proje
kökünden aşağıdaki komutu çalıştırın:

```powershell
.\deployment\New-ReleasePackage.ps1 -Version 0.6.0
```

Paket `outputs/releases/` altına yazılır. İçinde backend çalışma kaynakları, derlenmiş IIS site
dosyaları, production ayar şablonu ve operasyon betikleri bulunur; gerçek `.env`, veritabanı,
upload veya `node_modules` dosyaları pakete alınmaz.

## Güncelleme ve geri dönüş

1. MSSQL ve upload klasörünün birlikte geri yüklenebilir yedeğini alın.
2. Eski frontend build'i ve backend uygulama klasörünü sürüm etiketiyle saklayın.
3. Testleri çalıştırın; backend sürecini durdurun; yeni kodu kurun; migration'ı uygulayın.
4. Preflight, smoke test ve kritik kabul akışını çalıştırın.
5. Sorunda uygulama dosyalarını önceki sürüme döndürün. Migration downgrade yalnızca ilgili
   migration'ın veri kaybı etkisi incelendikten sonra uygulanmalıdır; aksi halde veritabanını
   yayın öncesi yedekten geri yükleyin.

## Operasyon

- `/api/health/live`: süreç canlılığı
- `/api/health/ready`: MSSQL bağlantı hazırlığı
- IT web arayüzündeki **Sistem İzleme**: MSSQL, upload alanı, çalışma süresi ve merkezi log görünümü
- `APP_LOG_FILE`: uygulama ve Uvicorn olaylarını güvenli JSON biçiminde tutan dönen log dosyası
- Kurumsal SIEM/Seq/ELK kullanıldığında JSON dosyalarını okuyan ajanı yapılandırın; hassas veri
  maskelemesini merkezi sistemde de koruyun.
- `FAILED` e-posta bildirimlerini ve SMTP bağlantı hatalarını izleyin.
- MSSQL ve upload yedeklerini aynı kurtarma noktasıyla düzenli olarak geri yükleme testine alın.
- Session secret değişirse tüm aktif oturumların kapanacağını planlayın.
