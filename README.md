🎬 SNU FilmFest — OTT Audience Map

This project is a Machine Learning web app for clustering students at SNU University based on their OTT, movie, and series preferences.

The app allows the Cultural Committee to upload survey CSVs and instantly visualize audience clusters for better film fest planning and OTT tie-ups.

---

   🚀 Features

- 📤 Upload survey CSVs (`movie_genre_top1`, `series_genre_top1`, `ott_top1`, `content_lang_top1`)
- 🤖 Auto column detection & cleaning (no strict naming required)
- 🔍 K-Means clustering with Silhouette evaluation
- 📊 Visual t-SNE cluster plot
- 💡 Cluster summaries with dominant genres & platforms
- 🌙 Beautiful dark UI with drag-and-drop file upload
- 📱 Fully mobile-responsive
- 🔗 Shareable public URL (via Railway Hosting)
- 📸 QR code access support

---

   🧩 Folder Structure

snufilmfest/
│
├─ flask_api/
│ ├─ app.py → Flask backend + API routes
│ ├─ ml_utils.py → ML clustering logic
│ ├─ frontend/
│ │ ├─ index.html
│ │ ├─ styles.css
│ │ └─ app.js
│ ├─ uploads/ → Temp folder for uploaded & processed files
│ ├─ requirements.txt → Python dependencies
│ └─ Procfile → Gunicorn start command for hosting
│
├─ .gitignore
└─ README.md


---

   🧠 Tech Stack

| Layer | Technology |
|-------|-------------|
| Frontend | HTML, CSS (responsive dark UI), JavaScript |
| Backend | Python Flask |
| ML | scikit-learn (KMeans, t-SNE, Silhouette) |
| Deployment | Gunicorn + Railway |
| Visualization | Matplotlib |
| QR Generation | qrcode (Python) |

---

   ⚙️ Local Setup (Windows / macOS / Linux)

1️⃣ Clone the Repository
git clone https://github.com/<your-username>/snufilmfest.git
cd snufilmfest/flask_api

2️⃣ Create Virtual Environment
python -m venv venv
.\venv\Scripts\activate     (Windows)
  or
source venv/bin/activate    (Mac/Linux)

3️⃣ Install Requirements
pip install -r requirements.txt

4️⃣ Run Flask App
python app.py

5️⃣ Open in Browser

Visit:
👉 http://127.0.0.1:5000

or
👉 http://<your-local-ip>:5000 (to test on mobile within same Wi-Fi)
