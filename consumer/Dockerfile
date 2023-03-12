FROM centos/python-38-centos7

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

USER root

WORKDIR /opt/app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --no-input -r requirements.txt

COPY consumer/app.py ./app.py

CMD sleep 15 && faust -A app worker -l info -p 6666
