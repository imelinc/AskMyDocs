import json
import os
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

# Límites “free-tier friendly”
MAX_INPUT_CHARS = 6000       # ~1500 tokens aprox.
MAX_OUTPUT_TOKENS = 500      # salida del modelo
MAX_OUTPUT_CHARS = 450       # recorte final visible

def _messages_payload(text: str) -> dict:
    # Recorte de seguridad en la entrada
    text = (text or "").strip()[:MAX_INPUT_CHARS]

    prompt = (
        "Resume en español el siguiente documento en un máximo de 450 caracteres. "
        "No uses comillas ni guiones. No incluyas nombre del documento ni fechas. "
        "No uses palabras como resumen ni conclusión. "
        "Si el texto es muy corto, no lo resumas: repítelo tal cual. "
        "Si el texto es largo, extrae ideas principales y resume en 450 caracteres. "
        "Si el texto está vacío, responde exactamente: No se pudo extraer contenido.\n\n"
        f"Texto:\n{text}"
    )

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
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

        # Claude 3 en Bedrock (Messages API):
        # data["content"] es una lista de bloques; tomamos el primero de tipo "text".
        blocks = data.get("content", []) or data.get("output", {}).get("content", [])
        out_text = ""
        if isinstance(blocks, list) and blocks:
            first = blocks[0] or {}
            out_text = first.get("text", "") or first.get("content", "")

        # Recorte final a 450 caracteres (coherente con el prompt)
        summary = (out_text or "").strip()[:MAX_OUTPUT_CHARS] or "No hubo respuesta del modelo."

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
