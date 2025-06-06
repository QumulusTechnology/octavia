#!/bin/bash


mv -f amphora-x64-haproxy-dev-latest.qcow2 amphora-x64-haproxy-2025.1-latest.qcow2
sha256sum amphora-x64-haproxy-2025.1-latest.qcow2 | cut -d " " -f1 > amphora-x64-haproxy-2025.1-latest.qcow2.SHA256SUM

mc cp amphora-x64-haproxy-2025.1-latest.qcow2 minio/qcp
mc cp amphora-x64-haproxy-2025.1-latest.qcow2.SHA256SUM minio/qcp
