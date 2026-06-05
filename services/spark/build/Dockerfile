ARG BASE_IMAGE=apache/spark:4.1.2
FROM ${BASE_IMAGE}

# apache/spark:4.1.2 ships hadoop-client-{api,runtime}-3.4.2 but does
# NOT include hadoop-aws or the AWS SDK v2 bundle. Without these, any
# s3a:// access throws ClassNotFoundException at runtime:
#   - spark-history can't read s3a://spark-history/ → empty UI forever
#   - spark-connect drivers can't write spark.eventLog.dir=s3a://… →
#     either silent log loss or hard failure depending on Spark policy
#   - Zeppelin's SPARK_SUBMIT_OPTIONS s3a:// access fails on first cell
#   - Airflow DAGs using Spark Connect to write parquet to s3a:// fail
#
# Hadoop 3.4.x's S3AFileSystem requires:
#   - hadoop-aws-3.4.2.jar (matches the bundled hadoop-client version)
#   - bundle-2.x.x.jar    (AWS SDK v2 shaded; declared as runtime dep
#                          in hadoop-aws's POM but NOT shaded into it)
#
# Drop both into /opt/spark/jars so they're on the driver+executor
# classpath without needing `--packages` at submit time.

USER root

# Versions: hadoop-aws MUST match hadoop-client (3.4.2). bundle version
# tracks what hadoop-aws-3.4.2's POM declares — verified at
# https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/3.4.2/hadoop-aws-3.4.2.pom
ARG HADOOP_AWS_VERSION=3.4.2
ARG AWS_SDK_BUNDLE_VERSION=2.29.52

RUN set -eux; \
    curl -fsSL -o /opt/spark/jars/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
        "https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar"; \
    curl -fsSL -o /opt/spark/jars/bundle-${AWS_SDK_BUNDLE_VERSION}.jar \
        "https://repo.maven.apache.org/maven2/software/amazon/awssdk/bundle/${AWS_SDK_BUNDLE_VERSION}/bundle-${AWS_SDK_BUNDLE_VERSION}.jar"

USER spark
