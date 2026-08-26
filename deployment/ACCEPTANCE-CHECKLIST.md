# V2 Üretim Kabul Kontrol Listesi

Tarih: __________  Ortam: __________  Uygulama sürümü: __________

Uygulayan USER: __________  Uygulayan IT: __________  Uygulayan ADMIN: __________

## Yayın ve güvenlik

- [ ] Site yalnızca geçerli HTTPS adresinden açılıyor; HTTP HTTPS'e yönleniyor.
- [ ] Port 8000 dış ağdan erişilemiyor.
- [ ] `/docs` ve `/redoc` production ortamında kapalı.
- [ ] `.env`, upload ve log alanlarının NTFS yetkileri en az yetki ilkesine uygun.
- [ ] MSSQL ile upload klasörünün yedekleme ve geri yükleme sorumluları belirlendi.
- [ ] IT Sistem İzleme ekranında MSSQL bağlı, dosya alanı yazılabilir ve log akışı güncel görünüyor.
- [ ] JSON log rotasyonu, saklama süresi ve disk doluluk uyarısı için operasyon sorumlusu belirlendi.
- [ ] Preflight ve `Smoke-Test.ps1` hatasız tamamlandı.

## Kritik uçtan uca akış

- [ ] USER izin verilen e-posta alan adıyla giriş yaptı.
- [ ] USER konu ve açıklama ile ticket oluşturdu; benzersiz `IT-000001` biçimli numara aldı.
- [ ] PNG/JPG/PDF eki doğru ticket'a eklendi ve yetkili kullanıcı tarafından indirildi.
- [ ] Ticket IT havuzunda göründü; yeni ticket sistem bildirimi ve e-postası ulaştı.
- [ ] IT öncelik belirledi ve ticket'ı üzerine aldı.
- [ ] IT çözüm açıklaması girmeden ticket'ı kapatamadı.
- [ ] IT çözüm açıklamasıyla ticket'ı kapattı.
- [ ] USER çözüm sistem bildirimini ve e-postasını aldı.
- [ ] USER geçmişte çözüm açıklamasını ve ekleri görebildi; çözülmüş ticket'ı değiştiremedi.
- [ ] IT rapor toplamları ticket havuzuyla eşleşti; Excel dosyası açıldı.
- [ ] ADMIN geçici parolayla IT hesabı oluşturdu; IT ilk girişte parolasını değiştirmeden işleme devam edemedi.
- [ ] USER kendi açık talebini nedenle sildi; talep normal listelerden kayboldu ve ADMIN geri yükledi.
- [ ] ADMIN aktif veya çözülmüş talebi nedenle sildi; denetim kaydında yapan kişi ve neden görüldü.
- [ ] USER çözüm yapan IT çalışanına 1–5 puan verdi ve puanı 7 gün içinde güncelleyebildi.
- [ ] ADMIN hazır yanıt oluşturdu; BT çalışanı bu yanıtı ticket sonuç açıklamasına ekleyebildi.
- [ ] BT çalışanı gelişmiş filtreleri, "Benim Ticketlarım" görünümünü ve Kanban görünümünü kullanabildi.
- [ ] Ticket etiketleme, takip etme ve işlem geçmişi ekranları doğru veriyi gösterdi.
- [ ] Eşit toplam puanda yalnızca liderlerden biri kazanan olarak seçilebildi.

## Yetki ve olumsuz senaryolar

- [ ] USER başka USER'ın tahmin edilen ticket/ek adresine erişemedi.
- [ ] USER IT endpoint'ine erişemedi ve kayıt isteğiyle IT rolü oluşturamadı.
- [ ] Hatalı uzantı, sahte MIME ve boyut sınırı üstü dosya reddedildi.
- [ ] İki IT'nin aynı ticket'ı eşzamanlı alma denemesinde yalnızca biri başarılı oldu.
- [ ] SMTP geçici olarak kapatıldığında ticket işlemi tamamlandı ve hata loglandı.
- [ ] Kullanıcı arayüzünde teknik traceback veya iç sunucu ayrıntısı gösterilmedi.

## Onay

Sonuç: [ ] Kabul  [ ] Koşullu kabul  [ ] Ret

Açıklamalar: ________________________________________________________________

İş birimi onayı: ____________________  Bilgi İşlem onayı: ____________________
