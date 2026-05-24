# Travel Buddy

[English](README.md) | [Turkce](README.tr.md)

YouTube seyahat videolarini ozetleyen, en iyi degerlendirilen mekanlari bulan ve yapay zeka destekli seyahat planlari olusturan bir komut satiri araci.

## Ozellikler

- **YouTube Video Ozetleme** — Bir YouTube linki yapistirir ve Turkce veya Ingilizce ozet alirsiniz
- **Mekan Onerileri** — Google Maps verileri ve yapay zeka destekli siralamayia en iyi restoranlari, gezilecek yerleri ve daha fazlasini bulun
- **Seyahat Plani Olusturma [Beta]** — Video bilgileri ve mekan onerilerini birlestirerek cok gunluk bir gezi plani olusturun *(bu ozellik calisiyor ancak kapsamli bir sekilde test edilmemistir)*

## Gereksinimler

Baslamadan once uc seye ihtiyaciniz var: **Python**, **ffmpeg** ve **API anahtarlari**.

### Adim 1: Python ve ffmpeg Kurulumu

<details>
<summary><strong>macOS</strong> (genisletmek icin tiklayin)</summary>

**Terminal** uygulamasini acin (Cmd+Space ile Spotlight'ta "Terminal" arayin).

**Xcode Komut Satiri Araclarini Kurun** (git ve derleme araclari icin gerekli):

```bash
xcode-select --install
```

Bir pencere acilacak — "Install"a tiklayin ve bitmesini bekleyin.

**Homebrew'i Kurun** (macOS icin paket yoneticisi):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Ekrandaki talimatlari izleyin. Bittiginde Homebrew'i PATH'e eklemek icin iki komut calistirmaniz istenebilir — bunlari kopyalayip calistirin.

**Python ve ffmpeg'i kurun:**

```bash
brew install python ffmpeg
```

**Her seyin calistigini dogrulayin:**

```bash
python3 --version
ffmpeg -version
```

Her ikisi icin de surum numaralari gormeniz gerekir.

</details>

<details>
<summary><strong>Windows</strong> (genisletmek icin tiklayin)</summary>

**Python Kurulumu:**

1. [python.org/downloads](https://www.python.org/downloads/) adresine gidin
2. En son Python 3 yukleyiciyi indirin
3. **Onemli:** "Install" a tiklamadan once **"Add Python to PATH"** kutusunu isaretleyin
4. "Install Now"a tiklayin

**ffmpeg Kurulumu:**

**Komut Istemi**ni acin (Baslat menusunde "cmd" arayin) ve calistirin:

```cmd
winget install ffmpeg
```

`winget` mevcut degilse, ffmpeg'i [ffmpeg.org/download.html](https://ffmpeg.org/download.html) adresinden indirin ve sistem PATH'inize ekleyin.

**Dogrulama:**

```cmd
python --version
ffmpeg -version
```

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong> (genisletmek icin tiklayin)</summary>

Terminal acin ve calistirin:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg
```

**Dogrulama:**

```bash
python3 --version
ffmpeg -version
```

</details>

### Adim 2: API Anahtarlari

Bu araci kullanmak icin en az bir API anahtarina ihtiyaciniz var. Hangi anahtarlara ihtiyaciniz oldugu kullanmak istediginiz ozelliklere baglidir:

| Ozellik | Gerekli Anahtarlar |
|---------|-------------------|
| YouTube Video Ozetleme | LLM API anahtari (OpenAI, Anthropic veya Ollama) |
| Mekan Onerileri | LLM API anahtari + Google Maps API anahtari |
| Seyahat Plani Olusturma | LLM API anahtari + Google Maps API anahtari |

#### Secenek A: OpenAI (varsayilan)

1. [platform.openai.com/api-keys](https://platform.openai.com/api-keys) adresine gidin
2. Hesap olusturun veya giris yapin
3. **"Create new secret key"** a tiklayin
4. Anahtari kopyalayin — bir sonraki adimda gerekecek

> OpenAI kullanim basina ucret alir. Tipik kullanim icin video basina birkac sent ve oneri sorgusu basina birkac sent bekleyin.

#### Secenek B: Anthropic

1. [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) adresine gidin
2. Hesap olusturun veya giris yapin
3. **"Create Key"** e tiklayin
4. Anahtari kopyalayin

#### Secenek C: Ollama (ucretsiz, yerel calisir)

Ollama, yapay zeka modellerini kendi bilgisayarinizda calistirir — API anahtari gerekmez, tamamen ucretsizdir.

1. [ollama.ai](https://ollama.ai) adresinden Ollama'yi kurun
2. Terminal acin ve calistirin: `ollama pull llama3.1`
3. Travel Buddy'yi kullanirken Ollama'yi arka planda calisiyor tutun

#### Google Maps API Anahtari

Mekan onerileri ve seyahat planlari icin gereklidir.

1. [console.cloud.google.com](https://console.cloud.google.com) adresine gidin
2. Yeni bir proje olusturun (veya mevcut birini secin)
3. **APIs & Services > Library** bolumune gidin
4. **Places API** arayin ve etkinlestirin
5. **Geocoding API** arayin ve etkinlestirin
6. **APIs & Services > Credentials** bolumune gidin
7. **"Create Credentials" > "API key"** e tiklayin
8. Anahtari kopyalayin

> Google ayda 200$ ucretsiz kredi verir, bu da tipik kisisel kullanimi karsilar.

## Kurulum

### macOS / Linux

```bash
git clone https://github.com/xingran815/travel-buddy.git
cd travel-buddy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

```cmd
git clone https://github.com/xingran815/travel-buddy.git
cd travel-buddy
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> Anthropic kullaniyorsaniz, ayrica calistirin: `pip install anthropic`

### API Anahtarlarinizi Yapilandirin

```bash
cp .env.example .env
```

Windows'ta `copy .env.example .env` kullanin.

`.env` dosyasini herhangi bir metin duzenleyicide acin ve API anahtarlarinizi girin:

```env
LLM_API_KEY=sk-openai-anahtariniz-buraya
GOOGLE_MAPS_API_KEY=AIza-google-anahtariniz-buraya
```

Anthropic ve Ollama yapilandirmasi dahil tum seenekler icin `.env.example` dosyasina bakin.

## Kullanim

### Etkilesimli Menu (onerilen)

Travel Buddy'yi kullanmanin en kolay yolu:

```bash
python main.py
```

Bu, ne yapacaginizi secebileceginiz bir menu acar:

```
1. YouTube Videosu Ozetle
2. Yer Onerileri Al
3. Seyahat Plani Olustur [Beta]
4. Ayarlar
q. Cikis
```

Yonlendirmeleri takip etmeniz yeterli — komut satiri deneyimi gerekmez.

### CLI Komutlari

Ileri duzey kullanicilar icin komutlari dogrudan kullanabilirsiniz:

**Video ozetleme:**

```bash
python main.py summarize "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Mekan onerileri:**

```bash
# Temel: bir bolgedeki en iyi 5 restoran
python main.py recommend "Istanbul" --type restaurant --top 5

# Kategoriye gore: yemek + gezilecek yerler
python main.py recommend "Paris" --category food,sights --top 3

# Tercihlerle
python main.py recommend "Tokyo" --type restaurant --cuisine japanese --budget 50 --profile foodie
```

**Seyahat plani olusturma:**

```bash
python main.py plan "Istanbul" --budget 500 --days 3 --preferences "history,food"
```

### Dil Degistirme

- **Menude:** "Ayarlar"i secin ve dilinizi secin
- **Komut satirinda:** `--lang en` veya `--lang tr` ekleyin
- **Kalici olarak:** `.env` dosyanizda `APP_LANG=en` veya `APP_LANG=tr` ayarlayin

## Yapilandirma

Tum ayarlar `.env` dosyasindadir. Temel secenekler:

| Degisken | Varsayilan | Aciklama |
|----------|-----------|----------|
| `LLM_API_KEY` | *(gerekli)* | Yapay zeka saglayicinizin API anahtari |
| `LLM_PROVIDER` | `openai` | Yapay zeka saglayicisi: `openai`, `anthropic` veya `ollama` |
| `LLM_MODEL` | `gpt-4o` | Kullanilacak model |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | API ucu noktasi |
| `GOOGLE_MAPS_API_KEY` | *(oneriler icin gerekli)* | Google Maps API anahtari |
| `APP_LANG` | `tr` | Arayuz dili: `en` veya `tr` |

## Proje Yapisi

```
travel-buddy/
  main.py              # Giris noktasi (CLI komutlari + etkilesimli menu)
  app/
    cli/               # CLI arguman isleme yardimlari
    i18n/              # Ceviriler (Ingilizce + Turkce)
    llm/               # Yapay zeka saglayici soyutlamasi (OpenAI, Anthropic, Ollama)
    places/            # Google Places API onbellekleme katmani
    planner/           # Seyahat plani olusturucu
    profile/           # Kullanici tercihleri saklama
    reviews/           # Mekan oneri motoru (puanlama, siralama)
    ui/                # Etkilesimli menu ve gosterim bicimlendirme
    youtube/           # YouTube ses indirme ve transkripsiyon
  tests/               # Test paketi
```

## Katki

Katkilar memnuniyetle karsilanir!

1. Depoyu forklayinn
2. Ozellik dali olusturun: `git checkout -b benim-ozelligim`
3. Degisikliklerinizi yapin
4. Testleri calistirin: `pytest`
5. Lint calistirin: `pylint app main.py`
6. Pull request gonderin

## Lisans

Bu proje MIT Lisansi altinda lisanslanmistir — ayrintilar icin [LICENSE](LICENSE) dosyasina bakin.
