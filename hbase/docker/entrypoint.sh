#!/usr/bin/env bash

set -euo pipefail

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  "${HBASE_HOME}/bin/hbase-daemon.sh" stop thrift >/dev/null 2>&1 || true
  "${HBASE_HOME}/bin/stop-hbase.sh" >/dev/null 2>&1 || true
  exit "${exit_code}"
}

wait_for_hbase() {
  local attempt
  for attempt in {1..60}; do
    if echo "status 'simple'" | "${HBASE_HOME}/bin/hbase" shell -n \
      >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  echo "HBase did not become ready within 120 seconds" >&2
  return 1
}

wait_for_thrift() {
  local attempt
  for attempt in {1..30}; do
    if curl --fail --silent --output /dev/null \
      http://127.0.0.1:9095/; then
      return 0
    fi
    sleep 1
  done

  echo "HBase Thrift did not become ready within 30 seconds" >&2
  return 1
}

services_are_running() {
  "${JAVA_HOME}/bin/jps" -l | grep -q "org.apache.hadoop.hbase.master.HMaster" \
    && "${JAVA_HOME}/bin/jps" -l \
      | grep -q "org.apache.hadoop.hbase.thrift.ThriftServer"
}

mkdir -p \
  /data/hbase \
  /data/logs \
  /data/tmp \
  /data/zookeeper \
  "${HBASE_PID_DIR}"

trap cleanup EXIT INT TERM

"${HBASE_HOME}/bin/start-hbase.sh"
wait_for_hbase
"${HBASE_HOME}/bin/hbase-daemon.sh" start thrift
wait_for_thrift

echo "HBase and Thrift are ready"

while services_are_running; do
  sleep 5
done

echo "HBase or Thrift stopped unexpectedly" >&2
exit 1
