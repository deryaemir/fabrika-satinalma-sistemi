# Fabrika Satınalma Talep ve Onay Yönetim Sistemi

Bu proje, fabrika satınalma süreçlerini dijitalleştirmek amacıyla geliştirilmiş PostgreSQL destekli mini ERP modülüdür. Sistem; satınalma talebi oluşturma, kullanıcı girişi, admin paneli, menü bazlı yetkilendirme, departman bazlı onay akışı, tedarikçi teklif yönetimi, sipariş oluşturma, mal kabul, fatura kontrolü ve dashboard raporlaması süreçlerini uçtan uca yönetir.

---

## Proje Amacı

Fabrika ortamında satınalma taleplerinin manuel takip edilmesi; onay süreçlerinde gecikme, teklif karşılaştırmalarında kontrol eksikliği, mal kabul takibinde belirsizlik ve raporlama zorlukları oluşturabilir.

Bu proje ile satınalma süreci dijital bir iş akışına dönüştürülerek daha izlenebilir, kontrollü, yetkilendirilebilir ve raporlanabilir hale getirilmiştir.

---

## Kullanılan Teknolojiler

- Python
- Streamlit
- PostgreSQL
- SQLAlchemy
- Pandas
- pgAdmin 4
- python-dotenv
- Role Based Access Control
- Dashboard ve CSV raporlama

---

## Proje Kapsamı

Bu proje, fabrika satınalma süreçlerinin dijitalleştirilmesi ve ERP mantığına uygun şekilde yönetilmesi amacıyla geliştirilmiştir.

Proje kapsamında aşağıdaki süreçler ele alınmıştır:

- Satınalma talebi oluşturma
- Kullanıcı adı ve şifre ile giriş sistemi
- Admin paneli üzerinden kullanıcı yönetimi
- Kullanıcı bazlı menü yetkilendirme
- Departman bazlı talep oluşturma
- Departman yöneticisi onay süreci
- Tutar bazlı otomatik onay akışı
- Satınalma, Finans ve Genel Müdür/Yönetim onayları
- Tedarikçi teklif girişi
- Teklif karşılaştırma
- Seçilen teklifin siparişe dönüştürülmesi
- Mal kabul süreci
- Fatura kontrolü
- Dashboard ve KPI raporlaması
- CSV çıktı alma
- PostgreSQL üzerinde ilişkisel veri yönetimi

Bu kapsamda proje; iş akışı otomasyonu, süreç optimizasyonu, kullanıcı yetkilendirme, veritabanı yönetimi ve operasyonel raporlama konularını içermektedir.

---

## Temel Özellikler

### Kullanıcı Girişi ve Yetkilendirme

- Kullanıcı adı ve şifre ile giriş yapılır.
- İlk admin kullanıcı sistem tarafından otomatik oluşturulur.
- Admin tüm sayfalara erişebilir.
- Admin Paneli üzerinden yeni kullanıcı eklenebilir.
- Kullanıcı bazlı menü yetkisi tanımlanabilir.
- Talep Oluştur ve Talep Listesi tüm kullanıcılara açıktır.
- Yetkisiz kullanıcılar ilgili sayfaya erişmeye çalıştığında uyarı alır.

Varsayılan admin bilgileri:

```text
Kullanıcı adı: itadmin
Şifre: Admin123!
```

---

### Satınalma Talebi Oluşturma

- Departman bazlı satınalma talebi oluşturulur.
- Talep eden kişi giriş yapan kullanıcıdan otomatik alınır.
- Admin dışındaki kullanıcıların departmanı otomatik gelir.
- TL ve USD para birimi desteği vardır.
- USD için döviz kuru girilerek TL karşılığı hesaplanır.
- Talep tutarına göre otomatik onay akışı belirlenir.
- Aciliyet ve kategoriye göre öncelik ve SLA tarihi hesaplanır.

---

### Onay Akışı

Talep tutarına göre onay seviyesi otomatik belirlenir.

| Tutar Aralığı | Onay Akışı |
|---|---|
| 0 - 5.000 TL | Departman Yöneticisi |
| 5.001 - 25.000 TL | Departman Yöneticisi + Satınalma |
| 25.001 - 100.000 TL | Departman Yöneticisi + Satınalma + Finans |
| 100.000 TL üzeri | Departman Yöneticisi + Satınalma + Finans + Genel Müdür / Yönetim |

Departman yöneticileri yalnızca kendi departmanlarına ait talepleri onaylayabilir.

Örneğin:

- İnsan Kaynakları talebi → İnsan Kaynakları Departman Yöneticisi
- Teknik Bakım talebi → Teknik Bakım Departman Yöneticisi
- Üretim talebi → Üretim Departman Yöneticisi

---

### Teklif Yönetimi

- Onayları tamamlanan talepler için tedarikçi teklifi girilebilir.
- Birden fazla tedarikçi teklifi karşılaştırılabilir.
- TL ve USD teklif girişi yapılabilir.
- Tekliflerin TL karşılığı otomatik hesaplanır.
- En düşük teklif sistem tarafından gösterilir.

---

### Siparişe Dönüştürme

- Girilen teklifler arasından bir teklif seçilir.
- Seçilen teklif satınalma siparişine dönüştürülür.
- Seçilen teklif işaretlenir.
- Talep durumu Mal Kabul Bekliyor olarak güncellenir.

---

### Mal Kabul

- Depo kullanıcısı siparişe ait mal kabul işlemi yapabilir.
- Teslim alınan miktar girilir.
- Mal kabul durumu seçilir.

Mal kabul durumları:

- Tam Kabul
- Eksik Kabul
- Hasarlı Ürün
- Reddedildi

Mal kabul sonrası talep Fatura Kontrolü Bekliyor durumuna geçer.

---

### Fatura Kontrolü

- Muhasebe veya Finans kullanıcısı fatura bilgilerini girer.
- Fatura tutarı ile sipariş tutarı karşılaştırılır.
- Fatura onaylanırsa süreç Tamamlandı olur.
- Fatura reddedilirse süreç incelemeye alınır.

---

### Dashboard

Dashboard ekranında aşağıdaki bilgiler takip edilebilir:

- Toplam talep sayısı
- Tamamlanan talep sayısı
- Onay bekleyen talep sayısı
- Geciken talep sayısı
- Departman bazlı talep sayısı
- Departman bazlı talep tutarı
- Kategori bazlı talep sayısı
- Öncelik bazlı talep sayısı
- Sipariş toplamları
- Fatura toplamları
- Seçilen teklif sayısı
- CSV çıktı alma

---

## Veritabanı Yapısı

Projede PostgreSQL üzerinde aşağıdaki tablolar kullanılmaktadır:

| Tablo | Açıklama |
|---|---|
| app_users | Kullanıcı bilgileri |
| user_permissions | Kullanıcı menü yetkileri |
| purchase_requests | Satınalma talepleri |
| approval_history | Onay geçmişi |
| supplier_offers | Tedarikçi teklifleri |
| purchase_orders | Satınalma siparişleri |
| goods_receipts | Mal kabul kayıtları |
| invoice_controls | Fatura kontrol kayıtları |

---

## Kullanım Akışı

1. Admin kullanıcısı ile giriş yapılır.
2. Admin Paneli üzerinden kullanıcılar oluşturulur.
3. Kullanıcılara erişebilecekleri menüler atanır.
4. Kullanıcı satınalma talebi oluşturur.
5. Departman yöneticisi kendi departmanına ait talebi onaylar.
6. Satınalma, Finans ve Yönetim onayları tamamlanır.
7. Tedarikçi teklifleri girilir.
8. Seçilen teklif siparişe dönüştürülür.
9. Depo mal kabul yapar.
10. Finans fatura kontrolünü tamamlar.
11. Dashboard üzerinden süreç takip edilir.

---

## Kurulum

### 1. Projeyi klonlayın

```bash
git clone https://github.com/deryaemir/fabrika-satinalma-sistemi.git
cd fabrika-satinalma-sistemi
```

### 2. Sanal ortam oluşturun

```bash
python -m venv venv
```

Windows için sanal ortamı aktif edin:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Bağımlılıkları kurun

```bash
pip install -r requirements.txt
```

### 4. `.env` dosyası oluşturun

Proje klasöründe `.env` dosyası oluşturun.

```env
DATABASE_URL=postgresql+psycopg2://postgres:SIFRENIZ@localhost:5432/factory_purchase_db
```

> `.env` dosyası GitHub’a yüklenmemelidir.

### 5. PostgreSQL server'ı başlatın

Örnek kullanım:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" -D "C:\postgres-data-17" -l "C:\Users\Derya\postgres-server.log" start
```

### 6. Uygulamayı çalıştırın

```bash
streamlit run app.py
```

---

## Varsayılan Admin Kullanıcısı

Uygulama ilk çalıştığında aşağıdaki admin kullanıcısı otomatik oluşturulur:

```text
Kullanıcı adı: itadmin
Şifre: Admin123!
```

Admin kullanıcı:

- Tüm menülere erişebilir.
- Admin Paneli üzerinden yeni kullanıcı ekleyebilir.
- Kullanıcı menü yetkilerini güncelleyebilir.

---

## Lisans

Bu proje eğitim, portföy ve süreç geliştirme amacıyla hazırlanmıştır.