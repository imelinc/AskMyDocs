import json, os, uuid, boto3
from urllib.parse import quote

s3 = boto3.client("s3")
BUCKET = os.environ.get("BUCKET_NAME", "askmydocs-imelinc-dev")

def lambda_handler(event, context):
    
    file_id = str(uuid.uuid4())
    
    params = event.get("queryStringParameters") or {}
    ext = (params.get("ext") or "pdf").lower()
    key = f"uploads/{file_id}.{ext}"

    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET, "Key": key, "ContentType": "application/pdf"},
        ExpiresIn=300,  
        HttpMethod="PUT",
    )
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps({"uploadUrl": url, "key": key, "displayKey": quote(key)})
    }

