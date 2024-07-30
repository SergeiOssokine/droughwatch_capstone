FROM public.ecr.aws/lambda/python:3.10

COPY ["requirements.txt","./"]
RUN pip install uv
RUN uv pip install --system --no-cache   -r requirements.txt

COPY [ "parse_data.py", "./" ]
COPY [ "lambda_function_processing.py", "./" ]
COPY [ "lambda_function_inference.py", "./" ]
COPY [ "lambda_function_observe.py", "./" ]

CMD [ "lambda_function_processing.lambda_handler" ]