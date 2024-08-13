from fastapi import FastAPI, Request, HTTPException, Response
from func.handler import handler

app = FastAPI()

def handle_get_request(request: Request):
    query_parameters = request.query_params
    path_parameters = request.path_params
    event = {
        "queryStringParameters": dict(query_parameters),
        "pathParameters": path_parameters,
        "body": None
    }
    
    context = {"fargate":True}

    response = handler(event, context)

    if 'body' not in response:
        raise HTTPException(status_code=500, detail="Malformed Lambda response")
    
    headers = response.get('headers', {})
    return Response(content=response['body'], status_code=response['statusCode'], headers=headers)


@app.get("/")
async def read_root(request: Request):
    return handle_get_request(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
