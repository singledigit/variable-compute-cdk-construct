def handler(event, context):
    response_text = 'Hello from Lambda'
    if 'fargate' in context and context['fargate']:
        response_text = 'Hello from Fargate'
    return {
        'statusCode': 200,
        'statusDescription': "200 ok",
        'isBase64Encoded': False,
        'headers': {
            "content-type": "text/html",
            "tester":"my-header",
        },
        'body': response_text
    }
