from fastapi import FastAPI, Request, HTTPException, Response
from func.handler import handler
import json

app = FastAPI()

def create_lambda_event(request: Request, body: str = None):
    """Create a Lambda-style event from a FastAPI Request"""
    headers = {key: value for key, value in request.headers.items()}
    
    # For multiValueHeaders, we handle headers with potential multiple values manually
    multi_value_headers = {}
    for key in request.headers:
        values = request.headers.getlist(key)
        multi_value_headers[key] = values

    # For multiValueQueryStringParameters, handle multiple values for query parameters
    multi_value_query_params = {}
    for key in request.query_params:
        values = request.query_params.getlist(key)
        multi_value_query_params[key] = values

    event = {
        "resource": request.url.path,
        "path": request.url.path,
        "httpMethod": request.method,
        "headers": headers,
        "multiValueHeaders": multi_value_headers,
        "queryStringParameters": dict(request.query_params) if request.query_params else None,
        "multiValueQueryStringParameters": multi_value_query_params if request.query_params else None,
        "pathParameters": request.path_params if request.path_params else None,
        "stageVariables": None,  # Can be customized if needed
        "requestContext": {
            "resourcePath": request.url.path,
            "httpMethod": request.method,
            "path": request.url.path,
            "protocol": request.scope.get("http_version", "HTTP/1.1"),
            # Add any other relevant request context attributes here
        },
        "body": body,
        "isBase64Encoded": False  # Set to True if the body should be base64-encoded
    }
    
    return event

def create_lambda_context():
    """Simulate a basic Lambda context object"""
    context = {
        "function_name": "your_lambda_function_name",
        "function_version": "$LATEST",
        "invoked_function_arn": "arn:aws:lambda:region:account-id:function:function-name",
        "memory_limit_in_mb": 128,
        "timeout": 3,  # Simulated timeout value
        "aws_request_id": "unique-request-id",  # Simulate request id
        "log_group_name": "/aws/lambda/your_lambda_function_name",
        "log_stream_name": "2023/08/14/[$LATEST]log-stream-id",
        # Add other context fields as needed
    }
    return context

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def catch_all(request: Request):
    body = await request.body()
    body_str = body.decode("utf-8") if body else None
    
    # Create a Lambda-like event and context
    event = create_lambda_event(request, body_str)
    context = create_lambda_context()

    # Call the Lambda handler function
    response = handler(event, context)

    if 'body' not in response:
        raise HTTPException(status_code=500, detail="Malformed Lambda response")

    headers = response.get('headers', {})
    
    return Response(content=response['body'], status_code=response['statusCode'], headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
