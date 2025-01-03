ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV TERM=xterm-256color
WORKDIR /code
COPY . /code/
RUN pip install --upgrade pip && pip install pybuilder faker progress1bar list2term
RUN pyb -X