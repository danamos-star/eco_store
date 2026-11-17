# 🌿 EcoStore
**Live Demo:** [https://ecostore-app-527805643521.us-central1.run.app](https://ecostore-app-527805643521.us-central1.run.app)  
*(Note: Use Stripe test card `4242 4242 4242 4242` with any future expiry and CVC to test checkout.)*

A full-stack serverless e-commerce web application built with **Python (Flask)** and hosted on **Google Cloud Run**. Designed around two core storefront experiences: a **Customer Storefront** and a password-protected **Seller Dashboard** with real-time catalog management, cloud media storage, and **Stripe Test Mode** checkout.

---

## ✨ Two core storefront experiences

### 🛍️ Customer storefront
* **Browse catalog:** View live eco-friendly product cards with images, categories, descriptions, and pricing.
* **Search and filter:** Query products dynamically by keyword or filter by category (*Home & Kitchen*, *Personal Care*, *Reusable Bags & Bottles*).
* **Shopping basket:** Add items client-side with real-time total calculation.
* **Card checkout:** Pay securely via **Stripe Checkout (Test Mode)** with automatic success and cancellation redirects.

### ⚙️ Seller dashboard (Admin mode)
* **Photo upload:** Stream validated product images (`PNG`, `JPG`, `WEBP`, `GIF`) directly to Google Cloud Storage.
* **Metadata storage:** Persist product titles, categories, pricing, descriptions, and public image URLs in Cloud Firestore.
* **Live edits and deletion:** Update product descriptions and pricing anytime, or delete products along with their associated Cloud Storage objects.
* **Zero maintenance:** Fully managed, auto-scaling serverless backend on Google Cloud Run.

---

## 🏗️ Serverless Google Cloud Architecture

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Compute and Routing** | Google Cloud Run (Python / Flask / Gunicorn) | Hosts the web application and handles customer & admin HTTP requests |
| **Media Storage** | Google Cloud Storage (GCS) | Stores public JPEG/PNG/WEBP/GIF product images |
| **Database** | Google Cloud Firestore (Native Mode) | NoSQL document database storing product metadata and image URLs |
| **Payments** | Stripe Checkout API | Processes test card checkout sessions securely in Sandbox mode |

### End-to-End Request and Data Flow
```text
[ Web Browser ] ──(HTTPS / Form Data)──▶ [ Cloud Run (Flask Server) ]
                                              ├──▶ Cloud Storage (Product Images)
                                              ├──▶ Firestore Native (Metadata & URLs)
                                              └──▶ Stripe Checkout (Test Card Payments)
```

[![Architecture diagram of danamos-star/eco_store](https://gitdiagram.com/danamos-star/eco_store/diagram.png)](https://gitdiagram.com/danamos-star/eco_store?utm_source=readme&utm_medium=picture)

## 📁 Project structure

```text
eco_store/
├── app.py                  # Flask application, Cloud Storage/Firestore logic, Stripe routes
├── templates/
│   └── index.html          # Responsive Customer Storefront & Seller Dashboard UI
├── Procfile                # Gunicorn production entrypoint for Cloud Run
├── requirements.txt        # Pinned Python dependencies
├── .gitignore              # Excludes secrets, virtual environments, and cache files
└── README.md               # Project documentation
```

---

## 🔐 Security practices

* **Environment-based configuration:** No API keys, bucket names, or admin credentials are hardcoded in source control.
* **Hardened sessions:** Uses `HttpOnly`, `Secure`, and `SameSite=Lax` session cookies signed with a cryptographic `FLASK_SECRET_KEY`, paired with constant-time password verification (`hmac.compare_digest`).
* **Upload and input validation:** Enforces MIME-type checks, sanitized filenames (`secure_filename`), a 5 MB upload size limit, and duplicate product name prevention.

🛡️ Optional Cloud cost and misuse hardening

To keep the deployment safely within Google Cloud's Always Free tier and protect against traffic spikes or misuse, the live demo includes the following optional safeguards:

* **Compute and scaling caps:** Configured a Cloud Run monthly spend cap, set `--max-instances=2` (with `--min-instances=0` scale-to-zero), and pinned Gunicorn to `--workers 1 --threads 8` to prevent runaway container scaling during traffic spikes.
* **Billing alerts:** Added a secondary project-wide alerts-only budget covering all GCP services (Firestore, Cloud Storage, Artifact Registry) with email notifications.
* **Brute-Force login protection:** Added IP-aware in-memory rate limiting (`X-Forwarded-For`) on `/admin/login` that locks out repeated failed password attempts for 10 minutes after 5 tries.
* **Database and catalog guardrails:** Enforced default-deny Firestore Security Rules (`allow read, write: if false;`) so only IAM-authenticated server code can access data, chained `.limit(50)` onto queries, and capped total catalog items at 30 products.
* **Storage and image optimization:** Configured Uniform bucket-level access (read-only `allUsers` viewer role), set `Cache-Control: public, max-age=86400` headers for edge caching, and added an Object Lifecycle rule to automatically delete incomplete multi-part uploads after 1 day.
* **Container Registry cleanup:** Added an Artifact Registry cleanup policy to automatically purge older container images after redeploys so image storage remains under the 500 MB free tier.
  
---

## 🚀 Deployment guide (Google Cloud Run)

### 1. Prerequisites
* A Google Cloud project with **Cloud Run**, **Cloud Firestore (Native mode)**, and **Cloud Storage** enabled.
* A public-read Cloud Storage bucket (`Storage Object Viewer` granted to `allUsers`) for serving product images.
* A **Stripe** account in **Test / Sandbox Mode**.

### 2. Required environment variables
Configure the following environment variables on your Cloud Run service:

| Variable | Description |
| :--- | :--- |
| `FLASK_SECRET_KEY` | Random cryptographic hex key used to sign Flask session cookies |
| `ADMIN_PASSWORD` | Strong password required to unlock Seller Dashboard controls |
| `BUCKET_NAME` | Name of your Google Cloud Storage bucket |
| `STRIPE_SECRET_KEY` | Your Stripe Sandbox/Test secret key (`sk_test_...` or `rk_test_...`) |

### 3. Deploy from Source
```bash
gcloud run deploy ecostore-app \
  --source . \
  --region us-central1 \
--allow-unauthenticated \
  --set-env-vars="BUCKET_NAME=your-bucket-name,FLASK_SECRET_KEY=your-random-secret,ADMIN_PASSWORD=your-strong-password,STRIPE_SECRET_KEY=your-stripe-test-key"
```
