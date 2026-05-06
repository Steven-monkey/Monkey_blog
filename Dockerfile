FROM python:3.12-slim

WORKDIR /app

RUN mkdir -p /app/data

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r /app/requirements.txt

COPY blog/ /app/blog/
COPY content/ /app/content/

ENV HOST=0.0.0.0
ENV PORT=8080
ENV SQLITE_PATH=/app/data/blog.db

EXPOSE 8080

CMD ["python", "-m", "blog.main"]
