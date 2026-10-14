# Lightweight Apache Hadoop 3.3.6 Single-Node Container with Python 3 Streaming
FROM eclipse-temurin:8-jdk-focal

ENV DEBIAN_FRONTEND=noninteractive
ENV HADOOP_VERSION=3.3.6
ENV HADOOP_HOME=/opt/hadoop
ENV HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
ENV JAVA_HOME=/opt/java/openjdk

# Install essential dependencies, OpenSSH, and Python 3 for Hadoop Streaming
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ssh \
    pdsh \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Download and extract Apache Hadoop 3.3.6 binary
RUN curl -fSL "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" -o /tmp/hadoop.tar.gz \
    && tar -xzf /tmp/hadoop.tar.gz -C /opt/ \
    && mv /opt/hadoop-${HADOOP_VERSION} $HADOOP_HOME \
    && rm -f /tmp/hadoop.tar.gz

# Configure passwordless SSH for single-node cluster
RUN ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa \
    && cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys \
    && chmod 0600 ~/.ssh/authorized_keys

# Set memory-tuned environment settings in hadoop-env.sh
RUN echo "export JAVA_HOME=${JAVA_HOME}" >> $HADOOP_CONF_DIR/hadoop-env.sh \
    && echo "export HADOOP_OS_TYPE=\${HADOOP_OS_TYPE:-\$(uname -s)}" >> $HADOOP_CONF_DIR/hadoop-env.sh \
    && echo "export HADOOP_NAMENODE_OPTS=\"-Xms128m -Xmx256m\"" >> $HADOOP_CONF_DIR/hadoop-env.sh \
    && echo "export HADOOP_DATANODE_OPTS=\"-Xms128m -Xmx256m\"" >> $HADOOP_CONF_DIR/hadoop-env.sh \
    && echo "export YARN_RESOURCEMANAGER_OPTS=\"-Xms128m -Xmx256m\"" >> $HADOOP_CONF_DIR/yarn-env.sh \
    && echo "export YARN_NODEMANAGER_OPTS=\"-Xms128m -Xmx256m\"" >> $HADOOP_CONF_DIR/yarn-env.sh

# Copy custom cluster XML configs and entrypoint
COPY core-site.xml $HADOOP_CONF_DIR/core-site.xml
COPY hdfs-site.xml $HADOOP_CONF_DIR/hdfs-site.xml
COPY mapred-site.xml $HADOOP_CONF_DIR/mapred-site.xml
COPY yarn-site.xml $HADOOP_CONF_DIR/yarn-site.xml
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Web UI and RPC ports
EXPOSE 9870 9000 8088 9864

WORKDIR /opt/hadoop

ENTRYPOINT ["/entrypoint.sh"]
