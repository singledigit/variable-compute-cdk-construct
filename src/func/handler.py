import os

def handler(event, context):
    response_text = 'Hello from Lambda'
    
    # Check if running in Fargate by looking for an environment variable
    if os.getenv('FARGATE', 'false').lower() == 'true':
        response_text = 'Hello from Fargate'
        
    return {
        'statusCode': 200,
        'statusDescription': "200 ok",
        'isBase64Encoded': False,
        'headers': {
            "content-type": "text/html",
            "tester": "my-header",
        },
        'body': response_text
    }
