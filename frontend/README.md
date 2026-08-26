# Destek Takip — Frontend

React, React Router ve Vite tabanlı USER, IT ve ADMIN arayüzü.

## Gereksinimler

- Node.js 22 veya üzeri
- `http://127.0.0.1:8000` adresinde çalışan backend

## Yerel kurulum ve çalıştırma

```powershell
cd frontend
npm ci
npm run dev
```

Uygulama adı `VITE_APP_NAME`, kayıt ekranı ise
`VITE_PUBLIC_REGISTRATION_ENABLED` build değişkeniyle özelleştirilebilir.

Arayüz `http://127.0.0.1:5173` adresinde açılır. Geliştirme sunucusu `/api` isteklerini
backend'e yönlendirir; oturum ve CSRF cookie'leri aynı origin üzerinden çalışır.

## Kalite komutları

```powershell
npm test
npm run lint
npm run build
```

Production derlemesi `dist/` klasörüne yazılır. Yayına alırken arayüz ile backend'in aynı
güvenli origin altında sunulması veya backend CORS/cookie ayarlarının gerçek origin'e göre
yapılandırılması gerekir.

## Ekranlar

- Kayıt, giriş ve profil
- Kullanıcı ana sayfası, ticket listesi, oluşturma ve detay
- Güvenli dosya eki yükleme/indirme/silme
- Kullanıcı ve IT bildirimleri
- IT özet paneli, aranabilir ticket havuzu ve ticket işlem ekranı
- Dönemsel rapor ve Excel dışa aktarma

Arayüz 320 piksel ve üzerindeki ekranlar için responsive tasarlanmıştır. Mobil görünümde menü
çekmeceye dönüşür; geniş tablolar sayfanın yerine kendi kartı içinde yatay kayar.
