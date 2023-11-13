FROM python:3-buster
RUN pip install --upgrade pip && pip install -U jetson-stats prometheus-client
RUN mkdir -p /root
COPY jetson_stats_prometheus_collector.py /root/jetson_stats_prometheus_collector.py
WORKDIR /root
USER root
RUN chmod +x /root/jetson_stats_prometheus_collector.py
ENTRYPOINT ["python3", "/root/jetson_stats_prometheus_collector.py"]