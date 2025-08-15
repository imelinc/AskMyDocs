import json, os, re
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

# Límites “free-tier friendly”
MAX_INPUT_CHARS   = 6000   # ≈ 1500 tokens aprox.
MAX_OUTPUT_TOKENS = 500    # salida del modelo (tokens)
MAX_OUTPUT_CHARS  = 450    # límite visible (caracteres)

END_TAG = "[END]"          # marca de fin

def _safe_truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    # intenta cortar en el último punto antes del límite
    cut = text.rfind(".", 0, limit)
    if cut == -1:
        # intenta cortar en el último espacio antes del límite
        cut = text.rfind(" ", 0, limit)
    if cut == -1:
        cut = limit
    return text[:cut].rstrip() + "…"

def _messages_payload(text: str) -> dict:
    text = (text or "").strip()[:MAX_INPUT_CHARS]

    # Pedimos que termine con [END] y limitamos longitud en el prompt
    prompt = (
        "Resume en español el siguiente documento en como máximo 450 caracteres. "
        "No uses comillas ni guiones. No incluyas nombres de documento ni fechas. "
        "No uses palabras como resumen ni conclusión. "
        "Si el texto es muy corto, repítelo tal cual. "
        "Si está vacío, responde exactamente: No se pudo extraer contenido. "
        f"Termina TU respuesta con {END_TAG} y no agregues nada luego.\n\n"
        f"Texto:\n{text}"
    )

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
        
        "stop_sequences": [END_TAG],
    }

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        text = (body.get("text") or "").strip()
        if not text:
            return _resp(400, {"error": "Falta 'text' en el body"})

        payload = _messages_payload(text)

        resp = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        data = json.loads(resp["body"].read())

        # Claude 3 (Messages API en Bedrock): content -> [{type:"text", text:"..."}]
        blocks = data.get("content", []) or data.get("output", {}).get("content", [])
        out_text = ""
        if isinstance(blocks, list) and blocks:
            first = blocks[0] or {}
            out_text = (first.get("text") or first.get("content") or "").strip()

        # Quita la marca [END] si hubiese quedado (por seguridad)
        out_text = out_text.replace(END_TAG, "").strip()

        # Truncado “inteligente” a 450 chars (sin cortar palabras)
        summary = _safe_truncate(out_text, MAX_OUTPUT_CHARS)
        if not summary:
            summary = "No hubo respuesta del modelo."

        return _resp(200, {"summary": summary})
    except Exception as e:
        return _resp(500, {"error": str(e)})

def _resp(code, obj):
    return {
        "statusCode": code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
            "Content-Type": "application/json",
        },
        "body": json.dumps(obj, ensure_ascii=False),
    }
