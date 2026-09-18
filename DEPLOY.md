# របៀប Deploy ទៅ Render.com (មាន link តែមួយប្រើបានគ្រប់កន្លែង)

គោលដៅ៖ បាន link ដូចជា `https://downland-video.onrender.com` ដែលគ្រប់ PC និងទូរស័ព្ទអាចប្រើបានពីគ្រប់ទីកន្លែង (មិនចាំបាច់បើកកុំព្យូទ័ររបស់អ្នក)។

មាន **៣ ដំណាក់កាល**៖
1. បង្កើត account (GitHub + Render) — ឥតគិតថ្លៃ
2. Upload code ទៅ GitHub
3. ភ្ជាប់ Render ទៅ GitHub → បាន link

---

## ដំណាក់កាលទី ១ — បង្កើត Account (ម្តងគត់)

1. **GitHub**: ចូល https://github.com/signup បង្កើត account (ឥតគិតថ្លៃ)
2. **Render**: ចូល https://render.com → ចុច "Get Started" → ជ្រើសរើស **Sign up with GitHub** (ភ្ជាប់ជាមួយ GitHub តែម្តង)

---

## ដំណាក់កាលទី ២ — Upload Code ទៅ GitHub

> គ្មាន Git លើកុំព្យូទ័រ? មិនអីទេ។ វិធីខាងក្រោមប្រើ **web browser** សុទ្ធ។

### បង្កើត Repository
1. ចូល https://github.com/new
2. **Repository name**: `downland-video`
3. ជ្រើសរើស **Public** (ឬ Private ក៏បាន)
4. **កុំ** tick "Add a README" (យើងមានហើយ)
5. ចុច **Create repository**

### Upload files
1. ក្នុងទំព័រ repo ថ្មី ចុច link **"uploading an existing file"**
   (ឬចូល `https://github.com/<username>/downland-video/upload/main`)
2. បើក folder `D:\05 APP\Downland Video` នៅលើកុំព្យូទ័រ
3. **អូស (drag) files និង folder ទាំងអស់** ចូលក្នុងទំព័រ GitHub៖
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `render.yaml`
   - `.gitignore`
   - `README.md`
   - folder `templates/` (ទាំង `index.html` ខាងក្នុង)

   > ⚠️ ត្រូវប្រាកដថា folder `templates` ត្រូវ upload ជាមួយ (មិនមែនត្រឹម index.html ដាច់ដោយឡែក)។ បើ drag folder មិនបាន សូម upload `index.html` រួច GitHub នឹងសួរ path — វាយ `templates/index.html`។
4. ចុះក្រោមចុច **Commit changes**

---

## ដំណាក់កាលទី ៣ — Deploy លើ Render

1. ចូល https://dashboard.render.com
2. ចុច **New +** → **Web Service**
3. ជ្រើសរើស repository `downland-video` (បើមិនឃើញ ចុច "Configure account" ដើម្បីអនុញ្ញាត Render ចូល GitHub)
4. Render នឹងអាន `render.yaml` ដោយស្វ័យប្រវត្តិ។ ពិនិត្យ setting៖
   - **Name**: `downland-video`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
   - **Plan**: **Free**
5. ចុច **Create Web Service**
6. រង់ចាំ ~2–5 នាទី (Render ដំឡើង dependencies និង build)។ ពេលឃើញ **"Live"** ពណ៌បៃតង = រួចរាល់!

**Link របស់អ្នក** នឹងបង្ហាញនៅខាងលើ ដូចជា៖
```
https://downland-video.onrender.com
```

Link នេះ **ចែករំលែកបាន** — គ្រប់គ្នា គ្រប់ PC គ្រប់ទូរស័ព្ទ ប្រើបានពីគ្រប់ទីកន្លែង។ 🎉

---

## ការ Update Code ពេលក្រោយ
ពេលអ្នកកែ code ថ្មី៖
1. Upload file ថ្មីទៅ GitHub (ជំនួសចាស់)
2. Render នឹង **re-deploy ស្វ័យប្រវត្តិ** — មិនចាំបាច់ធ្វើអ្វីទៀត

---

## ចំណាំសំខាន់ (Free Plan)
- **Sleep**: បើគ្មានគេប្រើ ~15 នាទី service នឹងដេក។ Request ដំបូងក្រោយពេលដេកអាចយឺត ~30–60 វិនាទី (បន្ទាប់មកលឿនធម្មតា)។ នេះជារឿងធម្មតារបស់ free plan។
- **Bandwidth**: Free plan មានកម្រិត bandwidth ខ្លះក្នុងមួយខែ។ បើប្រើច្រើនពេក អាចត្រូវ upgrade។
- **yt-dlp/TikTok API**: បើ TikTok/Facebook ផ្លាស់ប្តូររចនាសម្ព័ន្ធ អ្នកប្រហែលត្រូវ update yt-dlp (កែ version ក្នុង requirements.txt រួច upload ឡើងវិញ)។

---

## បើមានបញ្ហា (Troubleshooting)
- **Build បរាជ័យ**: មើល "Logs" tab លើ Render → រកមើលបន្ទាត់ error
- **App error / Internal Server Error**: ពិនិត្យ Logs → ភាគច្រើនជាបញ្ហា dependency ឬ typo
- **templates មិនឃើញ (TemplateNotFound)**: មានន័យថា folder `templates/` មិនបាន upload ត្រឹមត្រូវ → upload `templates/index.html` ម្តងទៀត

---

## ជម្រើសបន្ថែម៖ ប្រើ Git (បើក្រោយមកអ្នកដំឡើង Git)
```powershell
# នៅក្នុង folder គម្រោង
git init
git add .
git commit -m "Downland Video app"
git branch -M main
git remote add origin https://github.com/<username>/downland-video.git
git push -u origin main
```
បន្ទាប់មកធ្វើតាមដំណាក់កាលទី ៣ ដដែល។
