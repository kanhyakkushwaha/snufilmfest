"""
app.py - Flask backend for SNU FilmFest OTT Audience Clustering

Place this file in: snufilmfest/flask_api/app.py

Behavior:
- If a folder `flask_api/frontend/` exists (copy node_server/public here),
  Flask will serve the frontend at '/' and other static files automatically.
- POST /api/upload-and-analyze accepts a CSV file (form field "file") and a form field "k" (int number of clusters).
- The ML logic is delegated to ml_utils.run_clustering(csv_path, k, out_dir).
- Outputs (clusters.csv, plot_tsne.png) are saved to flask_api/uploads/ and served at /uploads/<filename>.
- CORS enabled for local dev. For production, restrict origins.
"""

import os
import time
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
from flask_cors import CORS
from ml_utils import run_clustering

# -------------------------
# Configuration
# -------------------------
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")  # put your index.html, app.js, styles.css here to serve from Flask
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"csv"}
MAX_CONTENT_LENGTH = 150 * 1024 * 1024  # 150 MB max upload

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=FRONTEND_DIR)
CORS(app)  # Development: allow cross-origin requests. In production, set origins explicitly.
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


# -------------------------
# Helpers
# -------------------------
def allowed_filename(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(storage_file, dest_folder, dest_name=None) -> str:
    """
    Save an uploaded Werkzeug FileStorage to dest_folder.
    Returns the absolute saved file path.
    """
    if dest_name:
        filename = secure_filename(dest_name)
    else:
        filename = secure_filename(storage_file.filename)
    # Add timestamp to avoid collisions
    name, ext = os.path.splitext(filename)
    timestamp = int(time.time() * 1000)
    filename_ts = f"{name}_{timestamp}{ext}"
    saved_path = os.path.join(dest_folder, filename_ts)
    storage_file.save(saved_path)
    return saved_path


# -------------------------
# Routes: Frontend serving or simple info
# -------------------------
@app.route("/", methods=["GET"])
def index():
    """
    Serve the frontend index.html if frontend folder exists.
    Otherwise return a small informational HTML page.
    """
    if os.path.isdir(FRONTEND_DIR) and os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
        return app.send_static_file("index.html")
    # Simple informational page
    return (
        "<h2>SNU FilmFest — ML Backend</h2>"
        "<p>This server provides the clustering API. Use the frontend (copy your static files to <code>flask_api/frontend/</code>) "
        "or call the API endpoint <code>/api/upload-and-analyze</code> (POST).</p>"
        "<ul>"
        "<li>API (POST): <code>/api/upload-and-analyze</code></li>"
        "<li>Uploaded/outputs: <code>/uploads/&lt;filename&gt;</code></li>"
        "</ul>"
    )


# serve any other static file requested from the frontend folder (app.js, styles.css, images...)
@app.route("/<path:path>", methods=["GET"])
def serve_static(path):
    if os.path.isdir(FRONTEND_DIR):
        # protect against directory traversal by leveraging Flask's static file serving
        return app.send_static_file(path)
    abort(404)


# -------------------------
# API: Upload & Analyze
# -------------------------
@app.route("/api/upload-and-analyze", methods=["POST"])
def upload_and_analyze():
    """
    Accepts multipart/form-data with:
      - file: CSV file (required)
      - k: optional int for number of clusters (default 4)
      - sample_limit: optional int to limit rows used in clustering (helps very large CSVs)
    Returns JSON with keys:
      - silhouette (float)
      - k (int)
      - notes (str)
      - plot_path (string filename within /uploads)
      - csv_path (string filename within /uploads)
      - summary (optional dict per-cluster)
    """
    # basic checks
    if "file" not in request.files:
        return "No file part in the request. Send a form with field 'file'.", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file (empty filename).", 400

    if not allowed_filename(file.filename):
        return f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}", 400

    # read params
    try:
        k = int(request.form.get("k", 4))
        if k < 1:
            raise ValueError
    except Exception:
        k = 4

    sample_limit = None
    try:
        sl = request.form.get("sample_limit", None)
        if sl is not None and sl != "":
            sample_limit = int(sl)
            if sample_limit <= 0:
                sample_limit = None
    except Exception:
        sample_limit = None

    # Save uploaded CSV with timestamped name
    try:
        saved_csv = save_uploaded_file(file, app.config["UPLOAD_FOLDER"])
    except Exception as e:
        return f"Failed to save uploaded file: {e}", 500

    # Run clustering (delegates to ml_utils.run_clustering)
    try:
        result = run_clustering(saved_csv, k=k, out_dir=app.config["UPLOAD_FOLDER"], sample_limit=sample_limit)
    except Exception as e:
        # include helpful debug info in development (but don't leak in production)
        return f"Clustering failed: {str(e)}", 500

    # Build response; ensure only basenames are sent (paths served from /uploads)
    plot_abspath = result.get("plot")
    clusters_csv_abspath = result.get("clusters_csv")
    plot_basename = os.path.basename(plot_abspath) if plot_abspath else None
    clusters_basename = os.path.basename(clusters_csv_abspath) if clusters_csv_abspath else None

    response = {
        "silhouette": float(result.get("silhouette", -1.0)),
        "k": int(k),
        "notes": result.get("notes", ""),
        "plot_path": plot_basename,
        "csv_path": clusters_basename,
    }
    if "summary" in result:
        response["summary"] = result["summary"]

    return jsonify(response)


# -------------------------
# Serve uploaded/generated files
# -------------------------
@app.route("/uploads/<path:filename>", methods=["GET"])
def serve_uploads(filename):
    """
    Serves files saved under flask_api/uploads/.
    Example: /uploads/plot_tsne.png or /uploads/clusters_123456789.csv
    """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)


# -------------------------
# Error handlers
# -------------------------
@app.errorhandler(413)
def request_entity_too_large(error):
    return "File is too large. Increase MAX_CONTENT_LENGTH on server if needed.", 413


@app.errorhandler(404)
def not_found(e):
    # Keep simple 404 message; frontend handles nicer UI
    return "Not Found", 404


# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    # Use debug=True for development only
    app.run(host="0.0.0.0", port=5000, debug=True)
