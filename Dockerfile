FROM python
USER root
WORKDIR /root
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash
RUN az extension add -n ml
RUN pip install --no-cache-dir apache-airflow
RUN mkdir -p airflow/dags
COPY dags/mlbuilder.py airflow/dags
EXPOSE 8080
COPY scripts/entrypoint.sh entrypoint.sh
RUN chmod u+x entrypoint.sh
ENTRYPOINT [ "/bin/bash", "entrypoint.sh" ]
