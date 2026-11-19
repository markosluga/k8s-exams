FROM python:3.15-slim

ENV PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TERM=xterm-256color \
    K8S_EXAM_PROGRESS_FILE=/progress/.progress.json

RUN pip install --no-cache-dir "rich>=13.0.0" \
    && useradd --create-home --uid 1000 kubestronaut \
    && mkdir /progress \
    && chown kubestronaut:kubestronaut /progress

WORKDIR /app
COPY k8s_exam_prep.py ./
COPY data ./data

USER kubestronaut
VOLUME /progress

ENTRYPOINT ["python", "k8s_exam_prep.py"]
