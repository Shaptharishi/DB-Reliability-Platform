
import os
import requests
from dotenv import load_dotenv

load_dotenv()

slack_webhook_url = os.environ.get("slack_webhook_url")


def send_slack_alert(rule_result):
    if rule_result is None:
        return

    if slack_webhook_url is None:
        print("slack_webhook_url not set -- skipping Slack notification")
        return

    severity = rule_result.get("severity", "warning")
    emoji = "🔴" if severity == "critical" else "🟡"

    text = (
        f"{emoji} *{severity.upper()}* — `{rule_result.get('rule')}`\n"
        f"{rule_result.get('message')}\n"
        f"Runbook: {rule_result.get('runbook')}"
    )

    try:
        response = requests.post(
            slack_webhook_url,
            json={"text": text},
            timeout=5
        )
        if response.status_code != 200:
            print(f"Slack notification failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Slack notification error: {e}")
