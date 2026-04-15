import json
import random
import time
import argparse
import sys
from datetime import datetime
from decimal import Decimal

# ==============================================================================
# BÖLÜM 1: AWS IOT CIHAZ SIMÜLATÖRÜ (Client Tarafı)
# AWS IoT Core'a MQTT üzerinden veri gönderecek olan Cihaz simülasyon kodları.
# İhtiyaç: pip install AWSIoTPythonSDK
# ==============================================================================
try:
    from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
except ImportError:
    # Lambda ortamında AWSIoTPythonSDK genelde bulunmaz, ImportError'u o yüzden eziyoruz.
    pass

def run_simulator(host, rootCAPath, certificatePath, privateKeyPath, clientId="iotSimulator", topic="iot/sensors"):
    """
    IoT cihazını simüle ederek AWS IoT Core'a sonsuz döngüde saniyede bir JSON verisi gönderir.
    """
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
    myAWSIoTMQTTClient.configureEndpoint(host, 8883)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

    myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)
    myAWSIoTMQTTClient.configureDrainingFrequency(2)
    myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)
    myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)

    print(f"AWS IoT Core'a bağlanılıyor: {host}...")
    myAWSIoTMQTTClient.connect()
    print("Bağlantı başarılı!")

    device_id = "sensor_" + str(random.randint(100, 999))

    try:
        while True:
            sicaklik = round(random.uniform(15.0, 35.0), 2)
            nem = round(random.uniform(30.0, 70.0), 2)
            timestamp = datetime.utcnow().isoformat() + "Z"

            payload = {
                "cihaz_id": device_id,
                "sicaklik": sicaklik,
                "nem": nem,
                "timestamp": timestamp
            }
            json_payload = json.dumps(payload)

            myAWSIoTMQTTClient.publish(topic, json_payload, 1)
            print(f"[{topic}] Topicine Veri Gönderildi: {json_payload}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nÇıkış yapılıyor...")
        myAWSIoTMQTTClient.disconnect()
        print("Bağlantı kapatıldı. Program sonlandı.")
        sys.exit(0)


# ==============================================================================
# BÖLÜM 2: AWS LAMBDA FONKSİYONU (Bulut Tarafı)
# AWS IoT Core Rule ile tetiklenen ve veriyi DB'ye kaydeden fonksiyon.
# İhtiyaç: Boto3 (Lambda içerisinde hazır gelir)
# ==============================================================================
try:
    import boto3
    dynamodb = boto3.resource('dynamodb')
    TABLE_NAME = 'HavaDurumuVerileri'
except ImportError:
    pass

def lambda_handler(event, context):
    """
    AWS IoT Core'dan tetiklenerek gelen veriyi DynamoDB'ye kaydeder.
    Eğer sıcaklık 30 dereceden büyükse duruma 'KRITIK' bilgisi ekler.
    """
    try:
        # Gelen veri doğrudan JSON string üzerinden geldiyse parse edilir
        if isinstance(event, str):
            payload = json.loads(event)
        else:
            payload = event

        cihaz_id = payload.get('cihaz_id')
        sicaklik = payload.get('sicaklik')
        nem = payload.get('nem')
        timestamp = payload.get('timestamp')

        print(f"Alınan Veri -> Cihaz: {cihaz_id}, Sıcaklık: {sicaklik}, Nem: {nem}")

        # Sıcaklık kontrolü
        if sicaklik is not None and float(sicaklik) > 30.0:
            payload['durum'] = 'KRITIK'
            print("Uyarı: Sıcaklık 30 dereceden büyük. Durum KRITIK olarak işaretlendi.")

        # DynamoDB ondalıklı sayılar için Float yerine Decimal bekler
        item_to_put = {
            'cihaz_id': cihaz_id,
            'timestamp': timestamp,
            'sicaklik': Decimal(str(sicaklik)) if sicaklik is not None else None,
            'nem': Decimal(str(nem)) if nem is not None else None
        }

        if 'durum' in payload:
            item_to_put['durum'] = payload['durum']

        # DynamoDB tablosuna kayıt
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=item_to_put)
        
        print("Veri DynamoDB tablosuna başarıyla kaydedildi.")

        return {
            'statusCode': 200,
            'body': json.dumps('Kayıt Başarılı.')
        }

    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Hata: {str(e)}')
        }


# ==============================================================================
# BÖLÜM 3: UYGULAMANIN LOKALDE ÇALIŞTIRILMASI 
# Lambda ortamındayken aşağıdaki blok es geçilir. Normal script olarak çalışır.
# ==============================================================================
# ==============================================================================
# BÖLÜM 3: UYGULAMANIN LOKALDE ÇALIŞTIRILMASI 
# Lambda ortamındayken aşağıdaki blok es geçilir. Normal script olarak çalışır.
# ==============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AWS IoT Cihaz Simülatörü")
    
    # Endpoint adresini sabitledik (required=False yaptık ve default olarak senin adresini girdik)
    parser.add_argument("-e", "--endpoint", action="store", required=False, default="abdfzu7kbbe5-ats.iot.eu-north-1.amazonaws.com", help="AWS IoT Core Endpoint")
    
    # Sertifika isimlerini sabitledik (Buradaki isimleri kendi dosyalarına göre değiştir!)
    parser.add_argument("-r", "--rootCA", action="store", required=False, default="root-CA.pem", help="Root CA Dosya Yolu")
    parser.add_argument("-c", "--cert", action="store", required=False, default="f8b794cd86dffbfab16c5dd2f174e17e948f0d631c016e660d6b85d67fc561e3-certificate.pem (1).crt", help="Certificate Dosya Yolu")
    parser.add_argument("-k", "--key", action="store", required=False, default="f8b794cd86dffbfab16c5dd2f174e17e948f0d631c016e660d6b85d67fc561e3-private.pem.key", help="Private Key Dosya Yolu")
    parser.add_argument("-id", "--client_id", action="store", default="BilisimProjeDevice1", help="Target Client ID")
    parser.add_argument("-t", "--topic", action="store", default="hava/durumu", help="Target Topic")
    args = parser.parse_args()
    
    # Simülasyonu başlat
    run_simulator(
        host=args.endpoint,
        rootCAPath=args.rootCA,
        certificatePath=args.cert,
        privateKeyPath=args.key,
        clientId=args.client_id,
        topic=args.topic
    )