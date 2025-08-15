import json, os, boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

def _messages_payload(text: str):
    # Recortamos por seguridad
    text = text[:20000]
    prompt = (
        "Resume en español el siguiente documento en un máximo de 500 caracteres. "
        "Sé claro y cubrí las ideas principales. Si el texto está vacío, decí 'No se pudo extraer contenido'.\n\n"
        f"Texto:\n{text}"
    )
    return {
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
        
        summary = data.get("output", {}).get("content", [{}])[0].get("text", "").strip()
        
        summary = summary[:500]

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
