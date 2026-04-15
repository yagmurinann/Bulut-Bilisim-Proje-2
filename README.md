# Gerçek Zamanlı Hava Durumu İzleme Sistemi

## Projenin Amacı
Bu proje, sensörlerden alınan sıcaklık ve nem verilerini bulut ortamına gerçek zamanlı olarak ileten, analiz eden ve depolayan bir IoT (Nesnelerin İnterneti) sistemi tasarlamayı amaçlamaktadır. "Bulut Bilişim" dersi kapsamında geliştirilen bu sistem ile cihazlardan okunan telemetri verilerinin AWS bulut altyapısı kullanılarak anlık takibi sağlanmaktadır. Ayrıca, belirli eşik değerlerin (örneğin; sıcaklığın 30°C'nin üzerine çıkması) aşılması durumunda verilere otomatik olarak "KRITIK" durumu atanarak verilerin zenginleştirilmesi hedeflenmiştir.

## Kullanılan Teknolojiler
Bu projede cihazdan buluta tüm veri akışı, modern, güvenilir ve ölçeklenebilir altyapılar kullanılarak gerçekleştirilmiştir:
* **MQTT Protokolü:** Hafif ağırlıklı bir mesajlaşma protokolü olup, uzak cihazlarda üretilen telemetri verilerinin düşük gecikme ve çok dar bant genişliklerinde dahi AWS IoT Core'a güvenli olarak aktarılması için kullanılmıştır.
* **Python (Boto3 & AWSIoTPythonSDK):** Uç cihaz (Edge) tarafında rastgele veri üretimi ile MQTT bağlantısının kurulması ve bulutta (AWS Lambda) verilerin işlenerek DynamoDB'ye aktarımı için temel programlama dili olarak tercih edilmiştir.
* **NoSQL (Amazon DynamoDB):** Sürekli zaman serisi formatında akan yüksek hacimli IoT verilerini düşük gecikmeyle (milisaniyeler seviyesinde) kalıcı olarak kaydetmek için yüksek yazma kapasiteli, tamamen yönetilen NoSQL veritabanı kullanılmıştır.

## Sistem Mimarisi Şeması Açıklaması
Projenin uçtan uca akışı temel olarak üç katmandan oluşmaktadır:
1. **IoT Cihaz Katmanı (AWS IoT Core):** Python ile yazılmış uç cihaz istemcisi (client), sensörden alınan (projede simüle edilen) çevre değişkenlerini (sıcaklık, nem, timestamp, cihaz_id) birleştirerek bir JSON pakedi haline getirir. Bu paket, belirlenen bir MQTT Topic'i (`iot/sensors`) üzerinden AWS IoT Core'a aktarılır.
2. **Kural ve İşlem Katmanı (AWS Lambda):** AWS IoT Core içine gelen JSON mesajı, tanımlanan bir "Message Routing Rule" (Kural) ile yakalanır ve doğrudan AWS Lambda fonksiyonuna yönlendirilir. Lambda fonksiyonu mesajı okur; iş kuralı gereği sıcaklık değeri 30°C'nin üzerindeyse, veri yapısına `"durum": "KRITIK"` bilgisini ekler.
3. **Depolama Katmanı (Amazon DynamoDB):** Lambda üzerinde kontrolü sağlanan son paket, Python üzerinden `Boto3` kullanılarak uzun süreli saklama için `HavaDurumuVerileri` isimli NoSQL tablosuna `PutItem` işlemi ile kaydedilir.

## Kurulum Adımları

Bu projenin baştan sona eksiksiz çalışması için hem bulut üzerinde hem de lokalde yapılması gereken işlemler aşağıda listelenmiştir.

### 1. AWS Bulut Ortamının Hazırlanması
* **DynamoDB Tablosu:** AWS Konsolundan DynamoDB servisine giderek `HavaDurumuVerileri` isminde bir tablo oluşturun. Tablonun Primary Key'lerini belirlerken **Partition Key** alanına `cihaz_id` (String), **Sort Key** alanına isteğe bağlı olarak `timestamp` (String) girmeniz tavsiye edilir.
* **IAM İzinleri Yeterliğinin Sağlanması:** AWS Lambda için kullanacağınız çalıştırma rolünün (Execution Role), DynamoDB üzerindeki bu tabloya `PutItem` yapabilmesi için yetkili olduğundan emin olun.
* **IoT Core Cihazının (Thing) Kaydı:** AWS IoT panelinde "Things" sekmesinden yeni bir cihaz tanımlayın. Oluşturma aşamasında size verilecek olan **Device Certificate**, **Private Key** ve **Root CA** sertifikalarını zorunlu olarak bilgisayarınıza indirin.
* **IoT Kuralı (Rule) Oluşturma:** IoT Core Message Routing konsoluna gidin, yeni bir kural (Rule) oluşturun. SQL sorgusu olarak `SELECT * FROM 'iot/sensors'` kullanın ve "Action" (Eylem) olarak tetiklenmesi için projedeki AWS Lambda fonksiyonunu seçin.

### 2. Lambda Fonksiyonunun Yayına Alınması
Projede hazırlanan `aws_iot_project.py` dosyası içindeki `lambda_handler` kısmını alarak AWS Lambda konsoluna kopyalayın ve kaydedin. 

### 3. Cihaz Simülatörünün Çalıştırılması
Lokal cihazınızın terminalini açın ve SDK bağlamları kurarak kendi cihaz sertifikalarınızı çalıştırın.

Gerekli SDK'nın kurulum komutu:
```bash
pip install AWSIoTPythonSDK
```

Uygulamanın çalıştırılması (Sertifikaların ve proje dosyasının aynı klasörde olduğu varsayılarak):
```bash
python aws_iot_project.py \
  -e <aws-iot-endpoint-adresiniz>-ats.iot.<region>.amazonaws.com \
  -r AmazonRootCA1.pem \
  -c <sertifika-id>-certificate.pem.crt \
  -k <sertifika-id>-private.pem.key \
  -id BilisimOdevi_Sensor_01 \
  -t iot/sensors
```

Komut terminalde çalışmaya başladığı andan itibaren, simülatör saniyede 1 kez veri üretir ve MQTT ile buluta "Publish" işlemi gerçekleştirir. Sistem akışı anlık takip edilerek verilerin DynamoDB üzerinde başarıyla oluştuğu saptanabilir.