FROM python:3.14-slim
WORKDIR /app
COPY app.py /app/app.py
COPY static/ /app/static/
RUN useradd --system --uid 10001 gallery
USER gallery
EXPOSE 8091
CMD ["python", "-u", "/app/app.py"]
