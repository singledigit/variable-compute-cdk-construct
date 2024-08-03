def handler(event, context):
    return {
        'statusCode': 200,
        'statusDescription': "200 ok",
        'isBase64Encoded': False,
        'headers': {
            "content-type": "text/html",
            "tester":"my-header",
        },
        'body': 'Hello from AWS Lambda'
    }
