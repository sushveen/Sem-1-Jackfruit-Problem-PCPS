from pathlib import Path

from flask import (
    Flask,
    request,
    render_template,
    jsonify,
    redirect,
    url_for,
)
from werkzeug.utils import secure_filename

from utils.file_ops import merge_files, count_errors
from utils.db_helpers import (
    get_student,
    update_student,
    get_all_students,
    add_student,
    get_all_resources,
    search_resources,
    add_resource,
)

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"   # folder already created by file_ops


# ------------------ PAGES ------------------ #

@app.route("/")
def home():
    resources = get_all_resources()
    students = get_all_students()
    return render_template(
        "index.html",
        resources_count=len(resources),
        students_count=len(students),
        title="Dashboard",
    )


@app.route("/resources", methods=["GET", "POST"])
def resources_page():
    # Add new resource
    if request.method == "POST":
        title = request.form.get("title")
        category = request.form.get("category")
        url = request.form.get("url")
        description = request.form.get("description") or ""
        add_resource(title, category, url, description)
        return redirect(url_for("resources_page", added=1))

    # Search / list
    query = request.args.get("q", "").strip()
    added = request.args.get("added") == "1"

    if query:
        resources = search_resources(query)
    else:
        resources = get_all_resources()

    return render_template(
        "resources.html",
        resources=resources,
        q=query,
        added=added,
        title="Resources",
    )


@app.route("/students", methods=["GET", "POST"])
def students_page():
    # Add or update student from form
    if request.method == "POST":
        mode = request.form.get("mode")
        if mode == "add":
            add_student(
                request.form.get("name"),
                request.form.get("course"),
                int(request.form.get("year") or 0),
                request.form.get("email"),
                request.form.get("notes") or "",
            )
            return redirect(url_for("students_page", added=1))
        elif mode == "update":
            sid = int(request.form.get("id"))
            update_student(
                sid,
                {
                    "name": request.form.get("name"),
                    "course": request.form.get("course"),
                    "year": int(request.form.get("year") or 0),
                    "email": request.form.get("email"),
                    "notes": request.form.get("notes") or "",
                },
            )
            return redirect(url_for("students_page", updated=1))

    students = get_all_students()
    added = request.args.get("added") == "1"
    updated = request.args.get("updated") == "1"

    return render_template(
        "student_records.html",
        students=students,
        added=added,
        updated=updated,
        title="Student Records",
    )


# ------------------ STUDENT API (JSON) ------------------ #

@app.route("/student/<int:sid>", methods=["GET", "PUT"])
def student_api(sid):
    if request.method == "GET":
        student = get_student(sid)
        if not student:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(student))
    else:
        data = request.get_json()
        update_student(sid, data)
        return jsonify({"status": "updated"})


# ------------------ FILE OPS ROUTES ------------------ #

@app.route("/merge-files", methods=["POST"])
def merge_files_route():
    """
    If file inputs are provided (file1, file2), save them and merge.
    If only text names provided (file1, file2), fall back to name-based merging.
    Returns JSON with merged file name.
    """
    # 1) Try file uploads
    f1 = request.files.get("file1")
    f2 = request.files.get("file2")

    if f1 and f1.filename and f2 and f2.filename:
        name1 = secure_filename(f1.filename)
        name2 = secure_filename(f2.filename)
        path1 = UPLOAD_DIR / name1
        path2 = UPLOAD_DIR / name2

        f1.save(path1)
        f2.save(path2)

        try:
            merged_name = merge_files(name1, name2)
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 400

        return jsonify({"merged_file": merged_name})

    # 2) Fallback: try old way (text input)
    file1_name = request.form.get("file1")
    file2_name = request.form.get("file2")
    if file1_name and file2_name:
        try:
            merged_name = merge_files(file1_name, file2_name)
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"merged_file": merged_name})

    return jsonify({"error": "No files provided"}), 400


@app.route("/count-errors")
def count_errors_route():
    log_name = request.args.get("log")
    try:
        result = count_errors(log_name)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


# ------------------ MAIN ------------------ #

if __name__ == "__main__":
    app.run(debug=True)
