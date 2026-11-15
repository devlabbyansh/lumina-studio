"""
app.py - LuminaCV Studio Backend Entry Point.
Flask web server managing image processing APIs, local storage, and session state.
"""

import os
import sys
import uuid
import base64
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, session, send_file, Response
from werkzeug.utils import secure_filename

# Ensure backend package can be imported from parent directory or local directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from config import Config
from image_ops import get_image_metadata, process_image, calculate_histogram, convert_to_svg
from nlp import parse_prompt

# Initialize Flask app pointing to root static and template directories
app = Flask(
    __name__,
    template_folder=os.path.join(Config.BASE_DIR, "templates"),
    static_folder=os.path.join(Config.BASE_DIR, "static"),
    static_url_path="/static"
)
app.config.from_object(Config)

# Ensure local uploads storage exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def generate_unique_filename(extension="png", prefix="orig"):
    return f"{prefix}_{uuid.uuid4().hex}.{extension}"


# -----------------------------------------------------------------------------
# Page Views
# -----------------------------------------------------------------------------

@app.route("/")
def index():
    # Session is preserved so user returning from /docs keeps active image
    return render_template("index.html")


@app.route("/docs")
def docs():
    return render_template("docs.html")


@app.route("/about")
def about():
    """Render About page with project information, prototype notice, and contact form."""
    return render_template("about.html")


@app.route("/api/contact", methods=["POST"])
def contact():
    """Receive and log bug reports and user feedback addressed to developwithansh@gmail.com."""
    data = request.get_json() or {}
    name = data.get("name", "Anonymous")
    email = data.get("email", "")
    category = data.get("category", "General")
    subject = data.get("subject", "Issue Report")
    message = data.get("message", "")

    if not email or not message:
        return jsonify({"success": False, "error": "Email and message are required."}), 400

    print(f"\n[Contact / Issue Report Recieved]")
    print(f"Target: developwithansh@gmail.com")
    print(f"Sender: {name} <{email}> | Category: {category} | Subject: {subject}")
    print(f"Content:\n{message}\n" + "-"*50)

    return jsonify({
        "success": True,
        "message": f"Thank you, {name}! Your report has been dispatched to developwithansh@gmail.com."
    })


# -----------------------------------------------------------------------------
# REST API Endpoints
# -----------------------------------------------------------------------------

@app.route("/api/session", methods=["GET"])
def get_session():
    """Retrieve active workspace state to restore canvas, slider, and history."""
    history = session.get("history")
    orig_name = session.get("original_image")

    if not history or not orig_name:
        return jsonify({"success": True, "has_session": False})

    current_idx = session.get("current_index", 0)
    if current_idx >= len(history):
        current_idx = len(history) - 1

    current_filename = history[current_idx]["filename"]
    original_filename = history[0]["filename"]

    current_path = os.path.join(app.config["UPLOAD_FOLDER"], current_filename)
    original_path = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)

    # Verify files still exist on disk
    if not os.path.exists(current_path) or not os.path.exists(original_path):
        session.clear()
        return jsonify({"success": True, "has_session": False})

    metadata = get_image_metadata(current_path)

    return jsonify({
        "success": True,
        "has_session": True,
        "filename": current_filename,
        "url": f"/static/uploads/{current_filename}",
        "original_url": f"/static/uploads/{original_filename}",
        "metadata": metadata,
        "history": history,
        "current_index": current_idx,
        "active_action": history[current_idx].get("action", "Original State")
    })


@app.route("/api/reset-session", methods=["POST"])
def reset_session():
    """Explicitly clear workspace session to start with a blank canvas."""
    session.pop("original_image", None)
    session.pop("history", None)
    session.pop("current_index", None)
    session.modified = True
    return jsonify({"success": True, "message": "Session reset successfully."})


@app.route("/upload", methods=["POST"])
def upload_image():
    """Receive an uploaded image file, store locally, and initialize history."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided in request."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not is_allowed_file(file.filename):
        return jsonify({"error": f"Invalid format. Allowed: {', '.join(app.config['ALLOWED_EXTENSIONS'])}"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = generate_unique_filename(ext, prefix="orig")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(filepath)

    metadata = get_image_metadata(filepath)

    # Initialize session
    session["original_image"] = unique_name
    session["history"] = [
        {"filename": unique_name, "action": "Uploaded original image"}
    ]
    session["current_index"] = 0
    session.modified = True

    return jsonify({
        "success": True,
        "filename": unique_name,
        "url": f"/static/uploads/{unique_name}",
        "original_url": f"/static/uploads/{unique_name}",
        "metadata": metadata,
        "history": session["history"],
        "current_index": 0
    })


@app.route("/demo", methods=["POST"])
def load_demo():
    """Generate an aesthetic demo banner directly into uploads folder."""
    unique_name = generate_unique_filename("png", prefix="orig")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)

    # Render a high-contrast photographic demo landscape
    h, w = 480, 560
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Sunset gradient background
    for y in range(h):
        ratio = y / float(h)
        b = int(25 + 40 * (1 - ratio))
        g = int(35 + 80 * ratio)
        r = int(210 - 70 * ratio)
        img[y, :] = (b, g, r)

    # Sun circle
    cv2.circle(img, (280, 220), 90, (40, 220, 255), -1)
    # Mountains contour
    pts_bg = np.array([[0, 360], [140, 240], [280, 320], [420, 210], [560, 340], [560, 480], [0, 480]], np.int32)
    cv2.fillPoly(img, [pts_bg], (70, 45, 60))
    pts_fg = np.array([[0, 420], [180, 320], [350, 410], [460, 300], [560, 400], [560, 480], [0, 480]], np.int32)
    cv2.fillPoly(img, [pts_fg], (35, 20, 30))

    cv2.putText(img, "LuminaCV Studio", (145, 450), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(filepath, img)

    metadata = get_image_metadata(filepath)

    session["original_image"] = unique_name
    session["history"] = [
        {"filename": unique_name, "action": "Uploaded original image"}
    ]
    session["current_index"] = 0
    session.modified = True

    return jsonify({
        "success": True,
        "filename": unique_name,
        "url": f"/static/uploads/{unique_name}",
        "original_url": f"/static/uploads/{unique_name}",
        "metadata": metadata,
        "history": session["history"],
        "current_index": 0
    })


@app.route("/chat", methods=["POST"])
def chat():
    """
    Execute image edits via NLP prompt string or direct { action, params } payload.
    Supports preset toolbar clicks, slider values, and chatbot instructions.
    """
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    explicit_action = data.get("action")
    explicit_params = data.get("params", {})

    if not prompt and not explicit_action:
        return jsonify({"error": "Empty prompt or action."}), 400

    history = session.get("history")
    if not history or "original_image" not in session:
        clean_p = (prompt or "").lower().strip()
        if any(g in clean_p for g in ["hi", "hello", "hey", "help", "what can you do"]):
            return jsonify({
                "reply": "Hi! Upload an image to the canvas or click **Load Demo Image** to start editing. You can then use the adjustment sliders, presets, or ask me in plain English!",
                "success": False
            })
        return jsonify({
            "reply": "Please upload an image first before applying edits.",
            "success": False
        })

    current_idx = session.get("current_index", 0)
    current_step = history[current_idx]
    current_filename = current_step["filename"]
    current_filepath = os.path.join(app.config["UPLOAD_FOLDER"], current_filename)

    # Resolve action & params
    if explicit_action:
        action = explicit_action
        params = explicit_params
    else:
        parsed = parse_prompt(prompt)
        if not parsed:
            return jsonify({
                "reply": f"I couldn't identify an operation for '{prompt}'. Check the Documentation for all available prompts, or try 'sharpen', 'saturate', 'cartoon', or 'vignette'!",
                "success": True,
                "url": f"/static/uploads/{current_filename}"
            })
        action = parsed["action"]
        params = parsed["params"]

    orig_filename = history[0]["filename"]

    # Handle Undo
    if action == "undo":
        if current_idx > 0:
            session["current_index"] = current_idx - 1
            session.modified = True
            undo_step = history[current_idx - 1]
            undo_filepath = os.path.join(app.config["UPLOAD_FOLDER"], undo_step["filename"])
            meta = get_image_metadata(undo_filepath)
            return jsonify({
                "reply": f"Undid last step. Restored state: **{undo_step['action']}**.",
                "success": True,
                "url": f"/static/uploads/{undo_step['filename']}",
                "original_url": f"/static/uploads/{orig_filename}",
                "metadata": meta,
                "history": history,
                "current_index": session["current_index"]
            })
        return jsonify({
            "reply": "You're at the original image state. Nothing to undo.",
            "success": True,
            "url": f"/static/uploads/{current_filename}",
            "original_url": f"/static/uploads/{orig_filename}"
        })

    # Handle Reset
    if action == "reset":
        session["current_index"] = 0
        session.modified = True
        orig_filepath = os.path.join(app.config["UPLOAD_FOLDER"], orig_filename)
        meta = get_image_metadata(orig_filepath)
        return jsonify({
            "reply": "Reset image to original state.",
            "success": True,
            "url": f"/static/uploads/{orig_filename}",
            "original_url": f"/static/uploads/{orig_filename}",
            "metadata": meta,
            "history": history,
            "current_index": 0
        })

    # Execute OpenCV transformation
    try:
        processed_img, msg = process_image(current_filepath, action, params)

        # Ensure correct file extension:
        # Images with alpha channel MUST be saved as .png; saving as .jpg discards transparency!
        has_alpha = len(processed_img.shape) == 3 and processed_img.shape[2] == 4
        if action in ("remove_bg", "remove_bg_color", "make_png") or has_alpha:
            ext = "png"
        elif action == "make_jpg":
            ext = "jpg"
        else:
            ext = current_filename.rsplit(".", 1)[1].lower() if "." in current_filename else "png"

        new_filename = generate_unique_filename(ext, prefix="proc")
        new_filepath = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
        cv2.imwrite(new_filepath, processed_img)

        # Truncate forward history if branching after an undo
        updated_history = history[: current_idx + 1]
        updated_history.append({
            "filename": new_filename,
            "action": msg
        })

        session["history"] = updated_history
        session["current_index"] = len(updated_history) - 1
        session.modified = True

        meta = get_image_metadata(new_filepath)

        return jsonify({
            "reply": f"{msg}",
            "success": True,
            "url": f"/static/uploads/{new_filename}",
            "original_url": f"/static/uploads/{orig_filename}",
            "metadata": meta,
            "history": updated_history,
            "current_index": session["current_index"]
        })
    except Exception as err:
        print(f"[app.py] Error during transformation: {err}")
        return jsonify({
            "reply": f"Error applying edit: {str(err)}",
            "success": False
        }), 500


@app.route("/api/histogram", methods=["GET"])
def get_histogram():
    """Return R, G, B histogram values for the active image."""
    history = session.get("history")
    if not history:
        return jsonify({"success": False, "error": "No active image."}), 400

    idx = session.get("current_index", len(history) - 1)
    filename = history[idx]["filename"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    data = calculate_histogram(filepath)
    if data:
        return jsonify({"success": True, "histogram": data})
    return jsonify({"success": False, "error": "Could not calculate histogram."}), 500


@app.route("/api/save-canvas", methods=["POST"])
def save_canvas():
    """Save canvas pixel data from manual background eraser brush as a new PNG step."""
    data = request.get_json() or {}
    image_data = data.get("image_data")
    if not image_data:
        return jsonify({"success": False, "error": "No image data provided."}), 400

    history = session.get("history")
    if not history or "original_image" not in session:
        return jsonify({"success": False, "error": "No active workspace session."}), 400

    # Extract base64 payload
    if "," in image_data:
        encoded = image_data.split(",", 1)[1]
    else:
        encoded = image_data

    try:
        decoded_bytes = base64.b64decode(encoded)
        np_arr = np.frombuffer(decoded_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            return jsonify({"success": False, "error": "Failed to decode canvas image."}), 400

        current_idx = session.get("current_index", len(history) - 1)
        new_filename = generate_unique_filename("png", prefix="proc")
        new_filepath = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
        cv2.imwrite(new_filepath, img)

        updated_history = history[: current_idx + 1]
        updated_history.append({
            "filename": new_filename,
            "action": "Manual Background Eraser"
        })

        session["history"] = updated_history
        session["current_index"] = len(updated_history) - 1
        session.modified = True

        meta = get_image_metadata(new_filepath)
        orig_filename = history[0]["filename"]

        return jsonify({
            "success": True,
            "reply": "Manual background eraser edits saved successfully.",
            "url": f"/static/uploads/{new_filename}",
            "original_url": f"/static/uploads/{orig_filename}",
            "metadata": meta,
            "history": updated_history,
            "current_index": session["current_index"]
        })
    except Exception as err:
        print(f"[app.py] Error saving canvas: {err}")
        return jsonify({"success": False, "error": str(err)}), 500


@app.route("/api/export", methods=["GET"])
def export_image():
    """Export current image with selected format (PNG, JPEG, WEBP, SVG) and quality."""
    history = session.get("history")
    if not history:
        return "No image to export", 400

    idx = session.get("current_index", len(history) - 1)
    filename = history[idx]["filename"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    fmt = request.args.get("format", "png").lower()
    quality = int(request.args.get("quality", 90))

    # Vector SVG Export
    if fmt == "svg":
        try:
            svg_content = convert_to_svg(filepath, num_colors=8)
            export_name = f"export_{uuid.uuid4().hex[:8]}.svg"
            export_path = os.path.join(app.config["UPLOAD_FOLDER"], export_name)
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            return send_file(
                export_path,
                mimetype="image/svg+xml",
                as_attachment=True,
                download_name="vector_artwork.svg"
            )
        except Exception as err:
            print(f"[app.py] SVG export error: {err}")
            return f"SVG generation failed: {str(err)}", 500

    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if img is None:
        return "Image not found", 404

    export_name = f"export_{uuid.uuid4().hex[:8]}.{fmt}"
    export_path = os.path.join(app.config["UPLOAD_FOLDER"], export_name)

    if fmt in ("jpg", "jpeg"):
        # If image has 4 channels (alpha), composite onto solid white background
        if len(img.shape) == 3 and img.shape[2] == 4:
            b, g, r, a = cv2.split(img)
            alpha_f = a.astype(float) / 255.0
            bg = np.ones_like(b, dtype=float) * 255.0
            b_out = (b * alpha_f + bg * (1.0 - alpha_f)).astype(np.uint8)
            g_out = (g * alpha_f + bg * (1.0 - alpha_f)).astype(np.uint8)
            r_out = (r * alpha_f + bg * (1.0 - alpha_f)).astype(np.uint8)
            bgr = cv2.merge([b_out, g_out, r_out])
        else:
            bgr = img if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(export_path, bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
        mimetype = "image/jpeg"
    elif fmt == "webp":
        cv2.imwrite(export_path, img, [cv2.IMWRITE_WEBP_QUALITY, quality])
        mimetype = "image/webp"
    else:  # PNG
        cv2.imwrite(export_path, img)
        mimetype = "image/png"

    return send_file(export_path, mimetype=mimetype, as_attachment=True, download_name=f"edited_image.{fmt}")


if __name__ == "__main__":
    print(f"LuminaCV Studio starting at http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)

