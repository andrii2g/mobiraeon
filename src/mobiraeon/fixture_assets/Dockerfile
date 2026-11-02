ARG BASE_IMAGE=python:3.14.10-slim-trixie
FROM ${BASE_IMAGE}
COPY program.py guard.py /fixture/
USER 65532:65532
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /tmp
ENTRYPOINT ["python", "-I", "/fixture/guard.py"]
