FROM python:3.9-buster

COPY requirements.txt .

RUN apt-get install -y g++ gcc libxslt chromium chromium-driver postgresql
RUN pip install -U -r requirements.txt