#define SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_RX   "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_TX   "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
#include "BLEDevice.h"
#include "BLEUtils.h"
#include "BLEServer.h"
BLECharacteristic *tx;
void snd(const char* s){tx->setValue((uint8_t*)s,strlen(s));tx->notify();}
void r1(const char* p,uint8_t b){char buf[16];sprintf(buf,"41%s%02X\r",p,b);snd(buf);return;}
void r2(const char* p,uint16_t v){char buf[16];sprintf(buf,"41%s%04X\r",p,v);snd(buf);return;}
void doCmd(const uint8_t* data,int len){
  String cm="";for(int i=0;i<len;i++)cm+=(char)data[i];cm.trim();
  if(cm=="ATZ"){snd("ELM327 v1.5\r");return;}
  if(cm=="ATI"){snd("ELM327 ELM327 v1.5\r");return;}
  if(cm.startsWith("AT")){snd("\r");return;}
  if(cm=="0101")r1("01",random(0,3));
  else if(cm=="0104")r1("04",map(random(10,90),0,100,0,255));
  else if(cm=="0105")r1("05",random(60,100)+40);
  else if(cm=="0106")r1("06",128+random(-10,10));
  else if(cm=="0107")r1("07",128+random(-5,5));
  else if(cm=="0108")r1("08",128+random(-8,8));
  else if(cm=="0109")r1("09",128+random(-3,3));
  else if(cm=="010A")r1("0A",128+random(-8,8));
  else if(cm=="010B")r1("0B",128+random(-3,3));
  else if(cm=="010C")r2("0C",random(700,6000)*4);
  else if(cm=="010D")r1("0D",random(0,180));
  else if(cm=="010E")r1("0E",128+random(-15,15));
  else if(cm=="010F")r1("0F",random(15,45)+40);
  else if(cm=="0110")r2("10",random(100,500));
  else if(cm=="0111")r1("11",map(random(0,40),0,100,0,255));
  else if(cm=="0112")r1("12",random(0,2)?0:0x80);
  else if(cm=="0114")r2("14",random(10,600));
  else if(cm=="0115")r2("15",random(1000,50000));
  else if(cm=="0119")r2("19",random(50,300));
  else if(cm=="011B")r2("1B",random(300,600));
  else if(cm=="011C")r2("1C",random(100,700));
  else if(cm=="011D")r2("1D",random(100,700));
  else if(cm=="011E")r2("1E",random(100,700));
  else if(cm=="011F")r2("1F",random(100,700));
  else if(cm=="0120")r2("20",random(100,700));
  else if(cm=="0121")r2("21",random(100,700));
  else if(cm=="0122")r2("22",random(100,700));
  else if(cm=="0123")r2("23",random(100,700));
  else if(cm=="012D")r1("2D",1);
  else if(cm=="012E")r1("2E",0);
  else if(cm=="0142")r2("42",random(12800,14200));
  else if(cm=="2101"){uint8_t buf[16];memset(buf,0,15);buf[0]=0x61;buf[1]=0x01;buf[14]=random(0,2)?0x20:0;tx->setValue(buf,16);tx->notify();return;}
  else snd("\r");
}
class WHandler:public BLECharacteristicCallbacks{void onWrite(BLECharacteristic* c){doCmd(c->getData(),c->getLength());}};
void setup(){
  Serial.begin(115200);randomSeed(analogRead(0));BLEDevice::init("ELM327");
  BLEServer *s=BLEDevice::createServer();BLEService *sv=s->createService(SERVICE_UUID);
  tx=sv->createCharacteristic(CHARACTERISTIC_TX,BLECharacteristic::PROPERTY_NOTIFY);
  tx->addDescriptor(new BLEDescriptor((char*)"2902",2));
  sv->createCharacteristic(CHARACTERISTIC_RX,BLECharacteristic::PROPERTY_WRITE)->setCallbacks(new WHandler());
  sv->start();BLEAdvertising *a=BLEDevice::getAdvertising();a->addServiceUUID(SERVICE_UUID);BLEDevice::startAdvertising();
  Serial.println("Started advertising");
}
void loop(){delay(10);}
