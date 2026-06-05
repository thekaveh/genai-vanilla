ARG BASE_IMAGE=apache/zeppelin:0.12.0
FROM ${BASE_IMAGE}

# apache/zeppelin:0.12.0 ships its own Spark interpreter
# (/opt/zeppelin/interpreter/spark/) but bundles only the AWS v1 SDK
# under /opt/zeppelin/plugins/NotebookRepo/S3NotebookRepo/ — that path
# is for notebook persistence to S3, NOT on the Spark interpreter
# classpath. The driver in client-mode runs inside this container; it
# parses `s3a://...` and needs hadoop-aws + AWS SDK v2 bundle on the
# Spark interpreter classpath, otherwise every notebook that reads or
# writes s3a:// throws ClassNotFoundException.
#
# Same fix pattern as services/spark/build/Dockerfile, dropped into
# /opt/zeppelin/interpreter/spark/ directly. Pass 45 originally placed
# them in a `dep/` subdir; Pass 47 caught that Zeppelin's
# `bin/interpreter.sh::addJarInDirForIntp` glob is `${INTERPRETER_DIR}/*`
# (non-recursive Java classpath wildcard) — `dep/*.jar` was invisible
# to the driver classpath. Placing them directly in the spark interp
# dir makes them picked up by the existing wildcard.

USER root

ARG HADOOP_AWS_VERSION=3.4.2
ARG AWS_SDK_BUNDLE_VERSION=2.29.52

RUN set -eux; \
    curl -fsSL -o /opt/zeppelin/interpreter/spark/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
        "https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar"; \
    curl -fsSL -o /opt/zeppelin/interpreter/spark/bundle-${AWS_SDK_BUNDLE_VERSION}.jar \
        "https://repo.maven.apache.org/maven2/software/amazon/awssdk/bundle/${AWS_SDK_BUNDLE_VERSION}/bundle-${AWS_SDK_BUNDLE_VERSION}.jar"; \
    chown 1000:1000 \
        /opt/zeppelin/interpreter/spark/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
        /opt/zeppelin/interpreter/spark/bundle-${AWS_SDK_BUNDLE_VERSION}.jar

USER 1000
