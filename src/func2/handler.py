import os

def handler(event, context):
    response_text = 'Hello from Lambda number 2'
    
    # Check if running in Fargate by looking for an environment variable
    if os.getenv('FARGATE', 'false').lower() == 'true':
        response_text = 'Hello from Fargate'
        
    # Extract the path from the event object, or return "not found" if it's missing
    request_path = event.get('path', 'not found')
    
    # Include the path in the response body
    response_body = f"{response_text}<br/>Path: {request_path}"
    
    return {
        'statusCode': 200,
        'statusDescription': "200 OK",
        'isBase64Encoded': False,
        'headers': {
            "content-type": "text/html",
            "tester": "my-header",
        },
        'body': response_body
    }
