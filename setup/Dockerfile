FROM apache/airflow:latest-python3.10

USER root
RUN apt-get update
# We need these later
RUN apt-get -y install procps git
USER airflow
ENV AIRFLOW_HOME=/usr/local/airflow


RUN pip install -U pip
RUN pip install -U  uv 

COPY [ "requirements.txt",  "./" ]

RUN uv pip install --no-cache -r requirements.txt

WORKDIR $AIRFLOW_HOME
COPY scripts scripts

USER $AIRFLOW_UID