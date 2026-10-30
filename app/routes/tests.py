from flask import Blueprint, jsonify, request
from ..database import get_db

tests_bp = Blueprint("tests", __name__, url_prefix="/api/tests")


@tests_bp.get("/")
def list_tests():
    db = get_db()
    tests = db.execute("SELECT * FROM tests ORDER BY created_at DESC").fetchall()
    db.close()
    return jsonify([dict(t) for t in tests])


@tests_bp.post("/")
def create_test():
    data = request.json
    name = data.get("name", "").strip()
    prompt = data.get("prompt", "").strip()

    if not name or not prompt:
        return jsonify({"error": "name and prompt required"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO tests (name, prompt) VALUES (?, ?)", (name, prompt)
    )
    db.commit()
    test_id = cur.lastrowid
    test = db.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
    db.close()
    return jsonify(dict(test)), 201


@tests_bp.put("/<int:test_id>")
def update_test(test_id):
    data = request.json
    name = data.get("name", "").strip()
    prompt = data.get("prompt", "").strip()

    if not name or not prompt:
        return jsonify({"error": "name and prompt required"}), 400

    db = get_db()
    db.execute(
        "UPDATE tests SET name = ?, prompt = ? WHERE id = ?", (name, prompt, test_id)
    )
    db.commit()
    test = db.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
    db.close()

    if not test:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(test))


@tests_bp.delete("/<int:test_id>")
def delete_test(test_id):
    db = get_db()
    db.execute("DELETE FROM tests WHERE id = ?", (test_id,))
    db.commit()
    db.close()
    return "", 204
