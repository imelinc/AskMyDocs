import json, os, boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

def _messages_payload(text: str):
    # Recorte básico por seguridad para no enviar textos enormes
    text = text[:20000].strip()
    prompt = (
        "Resume en español el siguiente documento en un máximo de 450 caracteres. "
        "Sé claro y cubrí las ideas principales. Si el texto está vacío, decí 'No se pudo extraer contenido'.\n\n"
        f"Texto:\n{text}"
    )
    return {
        # 👈 Requerido por Bedrock para modelos de Anthropic (Claude 3/3.5)
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
        "max_tokens": 600,
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

        # Para Messages API de Claude 3 en Bedrock:
        # data["content"] es una lista de bloques; tomamos el primero de tipo "text"
        blocks = data.get("content", []) or data.get("output", {}).get("content", [])
        summary = ""
        if blocks and isinstance(blocks, list):
            first = blocks[0] or {}
            summary = first.get("text", "") or first.get("content", "")
        summary = (summary or "").strip()[:500]

        return _resp(200, {"summary": summary or "No hubo respuesta del modelo."})
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
