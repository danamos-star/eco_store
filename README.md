# 🌿 EcoStore

A full-stack serverless e-commerce web application built with **Python (Flask)** and hosted on **Google Cloud Run**. Designed around two core storefront experiences—a **Customer Storefront** and a password-protected **Seller Dashboard**—with real-time catalog management, cloud media storage, and **Stripe Test Mode** checkout.

---

## ✨ Two Core Storefront Experiences

### 🛍️ Customer Storefront
* **Browse Catalog:** View live eco-friendly product cards with images, categories, descriptions, and pricing.
* **Search & Filter:** Query products dynamically by keyword or filter by category (*Home & Kitchen*, *Personal Care*, *Reusable Bags & Bottles*).
* **Shopping Basket:** Add items client-side with real-time total calculation.
* **Card Checkout:** Pay securely via **Stripe Checkout (Test Mode)** with automatic success and cancellation redirects.

### ⚙️ Seller Dashboard (Admin Mode)
* **Photo Upload:** Stream validated product images (`PNG`, `JPG`, `WEBP`, `GIF`) directly to Google Cloud Storage.
* **Metadata Storage:** Persist product titles, categories, pricing, descriptions, and public image URLs in Cloud Firestore.
* **Live Edits & Deletion:** Update product descriptions and pricing anytime, or delete products along with their associated Cloud Storage objects.
* **Zero Maintenance:** Fully managed, auto-scaling serverless backend on Google Cloud Run.

---

## 🏗️ Serverless Google Cloud Architecture

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Compute & Routing** | Google Cloud Run (Python / Flask / Gunicorn) | Hosts the web application and handles customer & admin HTTP requests |
| **Media Storage** | Google Cloud Storage (GCS) | Stores public JPEG/PNG/WEBP/GIF product images |
| **Database** | Google Cloud Firestore (Native Mode) | NoSQL document database storing product metadata and image URLs |
| **Payments** | Stripe Checkout API | Processes test card checkout sessions securely in Sandbox mode |

### End-to-End Request & Data Flow
```text
[ Web Browser ] ──(HTTPS / Form Data)──▶ [ Cloud Run (Flask Server) ]
                                              ├──▶ Cloud Storage (Product Images)
                                              ├──▶ Firestore Native (Metadata & URLs)
                                              └──▶ Stripe Checkout (Test Card Payments)
```
## 📁 Project Structure

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

## 🔐 Security Practices

* **Environment-Based Configuration:** No API keys, bucket names, or admin credentials are hardcoded in source control.
* **Hardened Sessions:** Uses `HttpOnly`, `Secure`, and `SameSite=Lax` session cookies signed with a cryptographic `FLASK_SECRET_KEY`, paired with constant-time password verification (`hmac.compare_digest`).
* **Upload & Input Validation:** Enforces MIME-type checks, sanitized filenames (`secure_filename`), a 5 MB upload size limit, and duplicate product name prevention.

---

## 🚀 Deployment Guide (Google Cloud Run)

### 1. Prerequisites
* A Google Cloud project with **Cloud Run**, **Cloud Firestore (Native mode)**, and **Cloud Storage** enabled.
* A public-read Cloud Storage bucket (`Storage Object Viewer` granted to `allUsers`) for serving product images.
* A **Stripe** account in **Test / Sandbox Mode**.

### 2. Required Environment Variables
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
  --allow-unauthenticated \
  --set-env-vars="BUCKET_NAME=your-bucket-name,FLASK_SECRET_KEY=your-random-secret,ADMIN_PASSWORD=your-strong-password,STRIPE_SECRET_KEY=your-stripe-test-key"
```
