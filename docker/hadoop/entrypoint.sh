#!/bin/bash
set -e

# Start SSH service for single-node intra-cluster communication
service ssh start

# Format NameNode on first run if not already formatted
if [ ! -d "/opt/hadoop/data/nameNode/current" ]; then
    echo "Formatting HDFS NameNode for single-node cluster..."
    $HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive
fi

# Start HDFS daemons (NameNode, DataNode, SecondaryNameNode)
echo "Starting HDFS daemons..."
$HADOOP_HOME/sbin/start-dfs.sh

# Start YARN daemons (ResourceManager, NodeManager)
echo "Starting YARN daemons..."
$HADOOP_HOME/sbin/start-yarn.sh

echo "Hadoop cluster is running."
echo "HDFS Web UI: http://localhost:9870"
echo "YARN Web UI: http://localhost:8088"

# Keep container in foreground by tailing the daemon logs
mkdir -p $HADOOP_HOME/logs
touch $HADOOP_HOME/logs/hadoop-root-namenode.log
exec tail -f $HADOOP_HOME/logs/*.log
