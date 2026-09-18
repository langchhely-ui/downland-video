# Downland Video

កម្មវិធី Web សម្រាប់ដោនឡូតវីដេអូពី **TikTok** និង **Facebook** ដោយ **គ្មាន Watermark**។

## លក្ខណៈពិសេស
- ✅ ដោនឡូត TikTok គ្មាន watermark (តាម tikwm.com API)
- ✅ ដោនឡូត Facebook (តាម yt-dlp)
- ✅ UI ងាយស្រួល បើកតាម browser ក៏បាន ទូរស័ព្ទក៏បាន
- ✅ រក្សាទុកជា MP4 ដោយផ្ទាល់

## ការដំឡើង (Setup)

ត្រូវការ **Python 3.8+**។

```powershell
# 1. បង្កើត virtual environment (ណែនាំ)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. ដំឡើង dependencies
pip install -r requirements.txt
```

## របៀបដំណើរការ (Run)

```powershell
python app.py
```

បន្ទាប់មកបើក browser ទៅកាន់៖ **http://localhost:5000**

បិទភ្ជាប់ link វីដេអូ រួចចុច **ដោនឡូត**។

## រចនាសម្ព័ន្ធ (Structure)

```
Downland Video/
├── app.py              # Flask backend
├── requirements.txt    # Dependencies
├── templates/
│   └── index.html      # Frontend UI
└── README.md
```

## របៀបប្រើលើទូរស័ព្ទ (ក្នុង WiFi តែមួយ)
1. រកលេខ IP កុំព្យូទ័រ (`ipconfig` → IPv4 Address)
2. បើកលើទូរស័ព្ទ: `http://<IP-កុំព្យូទ័រ>:5000`

## ចំណាំសំខាន់
- សម្រាប់ការប្រើប្រាស់ផ្ទាល់ខ្លួន ឬវីដេអូដែលអ្នកមានសិទ្ធិ។
- សូមគោរពសិទ្ធិម្ចាស់ស្នាដៃ (copyright) និងលក្ខខណ្ឌនៃ TikTok/Facebook។
- បើ TikTok API មិនដំណើរការ វានឹងប្តូរទៅប្រើ yt-dlp ដោយស្វ័យប្រវត្តិ។
- Facebook ខ្លះ (private/គ្មានសិទ្ធិ) មិនអាចដោនឡូតបានទេ។

## ដោះស្រាយបញ្ហា (Troubleshooting)
- **yt-dlp error**: ដំឡើងកំណែថ្មី `pip install -U yt-dlp`
- **Facebook មិនដំណើរការ**: link ត្រូវជាវីដេអូ public
