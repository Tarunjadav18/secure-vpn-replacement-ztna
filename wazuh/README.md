# Wazuh monitoring for the ZTNA demo

This optional integration collects the gateway's single-line JSON audit records with a Wazuh agent and evaluates example manager rules. It detects events; it does not supply trusted endpoint posture or control the gateway's access decisions.

## Prerequisites

- A running Wazuh manager and dashboard.
- A Wazuh agent installed on the same Mac/Linux host where the local Flask demo writes `/tmp/ztna-audit.jsonl`, enrolled with that manager, and connected.
- The gateway launched locally with `ZTNA_ADMIN_PASSWORD` set.

The agent and manager setup is not automated by this repository. Follow the official [Wazuh installation guide](https://documentation.wazuh.com/current/quickstart.html) for the supported deployment method.

## Configure the agent

Merge [`agent_localfile.xml`](agent_localfile.xml) into the existing agent `ossec.conf` inside its `<ossec_config>` element. Do not replace the agent's existing configuration. The sample monitors `/tmp/ztna-audit.jsonl` as JSON and adds a source label. If `ZTNA_AUDIT_LOG` is set to another path, change `<location>` to match that path.

Typical agent configuration locations are `/Library/Ossec/etc/ossec.conf` on macOS and `/var/ossec/etc/ossec.conf` on Linux. Restart the agent after editing its configuration. On macOS, the Wazuh agent control command is `/Library/Ossec/bin/wazuh-control restart`; on Linux installations using systemd, use `sudo systemctl restart wazuh-agent`.

## Configure the manager rules

Merge the rules in [`local_rules.xml`](local_rules.xml) into the manager's `/var/ossec/etc/rules/local_rules.xml`, preserving its surrounding `<group>` structure. The example raises alerts for a failed sign-in and denied app access, and a higher-level alert after five failed sign-ins from the same source IP within 120 seconds. Rule IDs `100501`–`100503` must not conflict with custom IDs already used by your manager. Validate the XML and test sample events with `/var/ossec/bin/wazuh-logtest` on the manager before restarting it.

The gateway writes events such as:

```json
{"time":1793700000,"event":"login_denied","user":"admin","source_ip":"127.0.0.1","detail":{"reason":"invalid_credentials"}}
```

After the agent reconnects, generate a failed login and a denied app request, then inspect the Wazuh dashboard's security events for the ZTNA rules. Log collection and rule matching have not been verified against a running Wazuh installation in this project environment; the example configs should be treated as integration material until validated with the manager's `wazuh-logtest` and a live agent.

## Hosted Render service

The local JSONL file is on the gateway host and Render's filesystem is ephemeral. A Wazuh agent on your Mac cannot read the Render container's audit file. For hosted monitoring, configure an authenticated, encrypted log-forwarding path to a collector you control, with explicit retention and network rules. Do not expose the Wazuh manager or its API publicly for this demo.

## Official references

- [Monitoring log files with Wazuh agents](https://documentation.wazuh.com/current/user-manual/capabilities/log-data-collection/monitoring-log-files.html)
- [Wazuh `localfile` configuration reference](https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html)
- [JSON decoder](https://documentation.wazuh.com/current/user-manual/ruleset/decoders/json-decoder.html)
- [Custom rules](https://documentation.wazuh.com/current/user-manual/ruleset/rules/custom.html)
