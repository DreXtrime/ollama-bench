from flask import Blueprint, jsonify, request, Response, stream_with_context
from ..ollama import get_models, pull_model
import json

models_bp = Blueprint("models", __name__, url_prefix="/api/models")


@models_bp.get("/")
def list_models():
    try:
        models = get_models()
        return jsonify(models)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@models_bp.post("/pull")
def pull():
    data = request.json
    model_name = data.get("model", "").strip()
    if not model_name:
        return jsonify({"error": "model name required"}), 400

    def generate():
        try:
            for event in pull_model(model_name):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")
