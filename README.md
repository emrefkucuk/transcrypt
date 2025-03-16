# Güvenli Dosya Transferi Uygulaması

Bu uygulama, güvenli bir şekilde gerçek zamanlı dosya transferi yapabilmenize olanak sağlar. Computer Security dersi projesi olarak tasarlanmıştır.

## Özellikler

- Secret key ile güvenli oda oluşturma
- WebSocket bağlantısı ile gerçek zamanlı dosya transferi
- Hem gönderici hem alıcı rollerini destekler
- Transfer ilerleme durumunu izleme
- Basit ve kullanıcı dostu arayüz

## Kurulum

1. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

2. Uygulamayı başlatın:
```bash
python main.py
```

3. Tarayıcınızda `http://localhost:8000` adresini ziyaret edin.

## Kullanım

### Dosya Göndermek İçin
1. "Yeni Oda Oluştur" butonuna tıklayın
2. Oluşturulan secret key'i alıcı ile paylaşın
3. "Gönderici Olarak Devam Et" butonuna tıklayın
4. Alıcının bağlantı kurmasını bekleyin
5. Dosya seçin ve "Dosya Gönder" butonuna tıklayın

### Dosya Almak İçin
1. "Odaya Katıl" butonuna tıklayın
2. Göndericinin size verdiği secret key'i girin
3. "Katıl" butonuna tıklayın
4. Gönderici dosya gönderdiğinde, otomatik olarak indirilecektir

## Güvenlik

Bu uygulama şu güvenlik önlemlerini içermektedir:
- Kriptografik olarak güvenli secret key üretimi
- WebSocket bağlantıları için anahtarla doğrulama
- İstemci tarafında veri doğrulama

Not: Bu uygulama eğitim amaçlı geliştirilmiştir. Şu an dosya içeriği şifrelenmeden aktarılmaktadır.
