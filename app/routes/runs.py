from flask import Blueprint, jsonify, request, Response, stream_with_context
from ..database import get_db
from ..ollama import run_prompt
import json

runs_bp = Blueprint("runs", __name__, url_prefix="/api/runs")


@runs_bp.get("/")
def list_runs():
    db = get_db()
    runs = db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 50").fetchall()
    db.close()
    return jsonify([dict(r) for r in runs])


@runs_bp.get("/<int:run_id>/results")
def run_results(run_id):
    db = get_db()
    results = db.execute("""
        SELECT r.*, t.name as test_name, t.prompt
        FROM results r
        JOIN tests t ON t.id = r.test_id
        WHERE r.run_id = ?
        ORDER BY t.name
    """, (run_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in results])


@runs_bp.post("/")
def create_run():
    data = request.get_json(silent=True) or {}

    model = (data.get("model") or "").strip()
    label = (data.get("label") or "").strip() or None

    if not model:
        return jsonify({"error": "model required"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO runs (model, label) VALUES (?, ?)",
        (model, label)
    )
    db.commit()

    run_id = cur.lastrowid
    db.close()

    return jsonify({"run_id": run_id}), 201


@runs_bp.post("/<int:run_id>/execute")
def execute_run(run_id):
    """Run all tests in a run, streaming results back as SSE."""
    data = request.get_json(silent=True) or {}
    test_ids = data.get("test_ids")  # optional, run a subset

    db = get_db()
    run = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not run:
        db.close()
        return jsonify({"error": "run not found"}), 404

    if test_ids:
        placeholders = ",".join("?" * len(test_ids))
        tests = db.execute(
            f"SELECT * FROM tests WHERE id IN ({placeholders})", test_ids
        ).fetchall()
    else:
        tests = db.execute("SELECT * FROM tests").fetchall()

    db.close()

    def generate():
        for test in tests:
            yield f"data: {json.dumps({'status': 'running', 'test_id': test['id'], 'test_name': test['name']})}\n\n"
            try:
                result = run_prompt(run["model"], test["prompt"])
                db2 = get_db()
                cur = db2.execute("""
                    INSERT INTO results (run_id, test_id, response, tokens_per_sec, first_token_ms, total_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    test["id"],
                    result["response"],
                    result["tokens_per_sec"],
                    result["first_token_ms"],
                    result["total_ms"],
                ))
                db2.commit()
                result_id = cur.lastrowid
                db2.close()

                yield f"data: {json.dumps({'status': 'done', 'test_id': test['id'], 'test_name': test['name'], 'result_id': result_id, **result})}\n\n"

            except Exception as e:
                db2 = get_db()
                db2.execute("""
                    INSERT INTO results (run_id, test_id, error)
                    VALUES (?, ?, ?)
                """, (run_id, test["id"], str(e)))
                db2.commit()
                db2.close()
                yield f"data: {json.dumps({'status': 'error', 'test_id': test['id'], 'test_name': test['name'], 'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@runs_bp.delete("/<int:run_id>")
def delete_run(run_id):
    db = get_db()
    db.execute("DELETE FROM results WHERE run_id = ?", (run_id,))
    db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    db.commit()
    db.close()
    return "", 204