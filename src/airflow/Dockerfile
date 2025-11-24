FROM apache/airflow:2.10.5-python3.12

# FROM apache/airflow:2.8.1-python3.9


COPY requirements.txt /requirements.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /requirements.txt


USER root

RUN apt update && \
    apt-get install -y openjdk-17-jdk && \
    apt-get install -y ant && \
    apt-get clean;
ENV PYTHONPATH=/opt
# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
RUN export JAVA_HOME

RUN mkdir -p /opt/airflow/logs && \
    chown -R airflow /opt/airflow/logs && \
    chmod -R 775 /opt/airflow/logs


    