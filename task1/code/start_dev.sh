#!/bin/bash
cd /root/research_deepagent
export PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin
exec agentseek dev > /root/agentseek_dev.log 2>&1
