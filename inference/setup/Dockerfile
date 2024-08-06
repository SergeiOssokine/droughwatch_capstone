FROM public.ecr.aws/lambda/python:3.10
ARG PREFIX=.
COPY ["${PREFIX}/requirements.txt","./"]
RUN pip install uv
RUN uv pip install --system --no-cache   -r requirements.txt

COPY [ "./training/airflow/includes/parse_data.py", "./" ]
COPY [ "${PREFIX}/lambda_function_processing.py", "./" ]
COPY [ "${PREFIX}/lambda_function_inference.py", "./" ]
COPY [ "${PREFIX}/lambda_function_observe.py", "./" ]
COPY [ "${PREFIX}/db_helper.py", "./" ]

CMD [ "lambda_function_processing.lambda_handler" ]