FROM python:3

RUN apt-get update && apt-get upgrade --yes

RUN apt-get install --yes ffmpeg python3-dev python3-pip git curl

ADD ./requirements.txt .

COPY requirements.txt /

RUN pip3 install -r /requirements.txt

ADD . /

CMD ["python3", "/main.py"]
