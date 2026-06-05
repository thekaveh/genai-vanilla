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
# /opt/zeppelin/interpreter/spark/dep/ which the Spark interpreter adds
# to its classpath at startup.

USER root

ARG HADOOP_AWS_VERSION=3.4.2
ARG AWS_SDK_BUNDLE_VERSION=2.29.52

RUN set -eux; \
    mkdir -p /opt/zeppelin/interpreter/spark/dep; \
    curl -fsSL -o /opt/zeppelin/interpreter/spark/dep/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
        "https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar"; \
    curl -fsSL -o /opt/zeppelin/interpreter/spark/dep/bundle-${AWS_SDK_BUNDLE_VERSION}.jar \
        "https://repo.maven.apache.org/maven2/software/amazon/awssdk/bundle/${AWS_SDK_BUNDLE_VERSION}/bundle-${AWS_SDK_BUNDLE_VERSION}.jar"; \
    chown -R 1000:1000 /opt/zeppelin/interpreter/spark/dep

USER 1000
