FROM apache/airflow:latest-python3.10

ENV AIRFLOW_HOME=/usr/local/airflow

RUN pip install -U pip
RUN pip install uv 

COPY [ "requirements.txt",  "./" ]

RUN uv pip install --no-cache -r requirements.txt

WORKDIR $AIRFLOW_HOME
COPY scripts scripts

USER $AIRFLOW_UID