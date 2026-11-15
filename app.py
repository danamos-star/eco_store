import hmac
import math
import os
import time
import uuid
from collections import OrderedDict
from urllib.parse import quote_plus, unquote

import stripe
from flask import Flask, redirect, render_template, request, session
from google.api_core.exceptions import NotFound
from google.cloud import firestore, storage
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Require secret key via environment variable (no hardcoded fallback)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config.update(
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 MB max upload size
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# Admin password configured via Cloud Run environment variable
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Initialize Google Cloud clients
db = firestore.Client()
bucket = storage.Client().bucket(os.environ["BUCKET_NAME"])

# Initialize Stripe with Test Secret Key
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_CATEGORIES = {"Home", "Personal Care", "Reusable"}

# In-memory brute-force protection for Admin Login
LOGIN_ATTEMPTS = OrderedDict()
MAX_FAILS = 5
LOCKOUT_SECONDS = 600  # 10 minutes
MAX_TRACKED_IPS = 1000


def is_valid_price(val: float) -> bool:
    return math.isfinite(val) and 0 < val <= 100000


def get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def is_ip_locked(ip: str):
    record = LOGIN_ATTEMPTS.get(ip)
    if not record:
        return False, 0
    remaining = record["locked_until"] - time.time()
    if remaining > 0:
        return True, int(remaining)
    LOGIN_ATTEMPTS.pop(ip, None)
    return False, 0


def record_failed_login(ip: str) -> None:
    if ip not in LOGIN_ATTEMPTS and len(LOGIN_ATTEMPTS) >= MAX_TRACKED_IPS:
        LOGIN_ATTEMPTS.popitem(last=False)

    record = LOGIN_ATTEMPTS.get(ip, {"fails": 0, "locked_until": 0})
    record["fails"] += 1
    if record["fails"] >= MAX_FAILS:
        record["locked_until"] = time.time() + LOCKOUT_SECONDS
    LOGIN_ATTEMPTS[ip] = record


# 1. STOREFRONT: Browse, Search, Filter & Conditional Admin View
@app.route("/")
def index():
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("cat", "").strip()
    msg = request.args.get("msg", "")
    err = request.args.get("err", "")

    docs = db.collection("products").limit(50).stream()
    items = [doc.to_dict() | {"id": doc.id} for doc in docs]

    if cat:
        items = [p for p in items if p.get("category") == cat]
    if q:
        items = [p for p in items if q in p.get("name", "").lower()]

    return render_template(
        "index.html",
        products=items,
        q=q,
        cat=cat,
        msg=msg,
        err=err,
        is_admin=session.get("is_admin", False),
    )


# 2. ADMIN AUTHENTICATION: Login (Rate-Limited) & Logout
@app.route("/admin/login", methods=["POST"])
def admin_login():
    ip = get_client_ip()
    locked, seconds_left = is_ip_locked(ip)
    if locked:
        minutes = max(1, (seconds_left + 59) // 60)
        return redirect(f"/?err={quote_plus(f'Too many failed attempts. Try again in {minutes} min.')}")

    submitted = request.form.get("password", "")
    if ADMIN_PASSWORD and hmac.compare_digest(submitted, ADMIN_PASSWORD):
        LOGIN_ATTEMPTS.pop(ip, None)
        session["is_admin"] = True
        return redirect("/?msg=Admin+mode+unlocked")

    record_failed_login(ip)
    return redirect("/?err=Incorrect+admin+password")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/?msg=Logged+out+of+admin+mode")


# 3. ADMIN ONLY: Add Product (With Duplicate Prevention & File Validation)
@app.route("/admin/add", methods=["POST"])
def add_product():
    if not session.get("is_admin"):
        return redirect("/?err=Unauthorised+access")

    try:
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        desc = request.form.get("desc", "").strip()
        price = float(request.form.get("price", 0))

        if not name or category not in ALLOWED_CATEGORIES or not is_valid_price(price):
            return redirect("/?err=Invalid+product+details")

        # Check Firestore for existing product with the same name (case-insensitive)
        existing_docs = list(db.collection("products").limit(50).stream())
        if len(existing_docs) >= 30:
            return redirect("/?err=Store+product+limit+reached+(30+max)")

        for doc in existing_docs:
            if doc.to_dict().get("name", "").strip().lower() == name.lower():
                return redirect(f"/?err={quote_plus(f'Product {name} already exists. Duplicate blocked.')}")

        img = request.files.get("photo")
        if not img or not img.filename or img.content_type not in ALLOWED_IMAGE_TYPES:
            return redirect("/?err=Please+upload+a+valid+image+(PNG,+JPG,+WEBP,+GIF)")

        safe_name = secure_filename(img.filename) or "product.png"
        unique_filename = f"{uuid.uuid4()}_{safe_name}"
        img.seek(0)
        blob = bucket.blob(unique_filename)
        blob.cache_control = "public, max-age=86400"
        blob.upload_from_file(img, content_type=img.content_type)

        db.collection("products").add({
            "name": name,
            "category": category,
            "price": round(price, 2),
            "desc": desc,
            "image_url": blob.public_url,
        })
        return redirect(f"/?msg={quote_plus(f'Added {name} to store')}")
    except Exception:
        app.logger.exception("Failed to add product")
        return redirect("/?err=Failed+to+upload+product")


# 4. ADMIN ONLY: Edit Product Price & Description
@app.route("/admin/edit/<product_id>", methods=["POST"])
def edit_product(product_id):
    if not session.get("is_admin"):
        return redirect("/?err=Unauthorised+access")

    try:
        price = float(request.form.get("price", 0))
        desc = request.form.get("desc", "").strip()
        if not is_valid_price(price) or not desc:
            return redirect("/?err=Invalid+price+or+description")

        db.collection("products").document(product_id).update({
            "price": round(price, 2),
            "desc": desc,
        })
        return redirect("/?msg=Product+updated")
    except Exception:
        app.logger.exception("Failed to update product")
        return redirect("/?err=Failed+to+update+product")


# 5. ADMIN ONLY: Delete Product Metadata & Cloud Storage Photo
@app.route("/admin/delete/<product_id>", methods=["POST"])
def delete_product(product_id):
    if not session.get("is_admin"):
        return redirect("/?err=Unauthorised+access")

    doc_ref = db.collection("products").document(product_id)
    doc = doc_ref.get()

    if doc.exists:
        image_url = doc.to_dict().get("image_url", "")
        if image_url:
            blob_name = unquote(image_url.split("/")[-1])
            try:
                bucket.blob(blob_name).delete()
            except NotFound:
                pass
        doc_ref.delete()

    return redirect("/?msg=Product+and+image+deleted")


# 6. CUSTOMER CHECKOUT: Stripe Test Card Mode
@app.route("/checkout", methods=["POST"])
def checkout():
    try:
        total_amount = float(request.form.get("total", 0))
        if not is_valid_price(total_amount):
            return redirect("/")

        base_url = (
            request.host_url.replace("http://", "https://")
            if "run.app" in request.host_url
            else request.host_url
        )
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "EcoStore Order"},
                    "unit_amount": int(round(total_amount * 100)),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=base_url + "?msg=Payment+successful!+Thank+you+for+your+order.",
            cancel_url=base_url,
        )
        return redirect(checkout_session.url, code=303)
    except Exception:
        app.logger.exception("Stripe checkout failed")
        return redirect("/?err=Checkout+failed.+Please+try+again.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
