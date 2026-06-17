# Responsible-Use Write-Up

## Project title

**AI-Assisted Defensive Cybersecurity Mini-Project: Real-Time Phishing Analysis and Log Triage with Responsible-Use Write-Up**

## Defensive purpose

This project is designed for defensive cybersecurity education. It helps a student learn how to build a small real-time analysis system that can:

- Classify sanitized email/text as `legitimate` or `phishing`.
- Classify sanitized URLs as `legitimate` or `phishing` using explainable structural features.
- Triage sanitized Apache/Nginx-style log lines for suspicious or anomalous patterns.
- Demonstrate real-time prediction through FastAPI endpoints and a simple frontend.
- Optionally support external URL reputation checks when the user explicitly opts in.

The system is intended for local learning, classroom demos, toy data, public safe datasets, and user-provided examples that the user has permission to analyze.

## Activities this project must not perform

This project must not be used to:

- Generate phishing emails, malicious websites, credential-harvesting pages, or social engineering content.
- Steal, collect, transmit, or store credentials, tokens, session cookies, one-time passcodes, or private keys.
- Attack, scan, exploit, disrupt, or probe websites, networks, APIs, or accounts.
- Scrape real inboxes, production logs, or private systems without explicit written permission.
- Submit private URLs, password reset links, internal hostnames, or sensitive personal data to third-party reputation services.
- Make automated security decisions without human review.

## Privacy and data privacy

The project should use only:

- Sanitized CSV datasets.
- Toy examples written for learning.
- Public datasets whose license and privacy constraints allow educational use.
- User-provided text, URLs, or logs that the user has permission to analyze.

The project should not include:

- Real credentials or passwords.
- Private reset links.
- Session IDs or API tokens.
- Personal inbox messages.
- Production server logs containing personal data or private infrastructure details.

The `.env` file is ignored by Git and should store local API keys only. Real API keys must never be committed.

## External threat-intelligence privacy

Phase 5 adds optional VirusTotal and PhishTank support. These services can provide useful reputation context, but they also introduce privacy risks.

Before enabling external checks, remember:

- The submitted URL may be sent to a third-party provider.
- The provider may store, process, or share submitted indicators according to its own policies.
- The project should not submit sensitive URLs, private reset links, internal-only hostnames, or links containing tokens.
- External checks are disabled by default and require `include_external_checks: true`.
- The system still works locally without API keys.

## False positives

A false positive happens when a legitimate message, URL, or log line is flagged as suspicious or phishing.

Possible causes:

- Legitimate security emails may use words like `verify`, `password`, or `urgent`.
- Legitimate URLs can contain hyphens, many subdomains, or login-related words.
- Normal web traffic can produce `404`, `401`, or `403` responses.
- A small beginner dataset cannot represent all normal behavior.

Impact:

- Users may waste time investigating harmless items.
- Too many false alerts can cause alert fatigue.
- A user may incorrectly distrust a legitimate service.

Mitigation:

- Use the tool as an assistive signal, not a final decision-maker.
- Review the reasons and raw input manually.
- Improve datasets with more representative benign examples.
- Tune thresholds after testing with sanitized data.

## False negatives

A false negative happens when a real phishing message, malicious URL, or suspicious log line is classified as safe or low risk.

Possible causes:

- Attackers can avoid obvious suspicious words.
- URLs can be short, HTTPS-enabled, and still malicious.
- New phishing campaigns may not match the training dataset.
- Rule-based log checks may miss subtle or low-and-slow behavior.
- External providers may not have seen a new URL yet.

Impact:

- A risky item may be missed.
- Users may trust an unsafe message or URL.
- Security teams may overlook suspicious activity.

Mitigation:

- Keep human review in the workflow.
- Use multiple signals, including model output, heuristics, and reputation checks when appropriate.
- Continue improving the dataset and rules.
- Document model limitations clearly during demos.

## Dataset bias and quality limitations

The included starter datasets are intentionally small and sanitized. They are useful for learning the workflow, but they are not production datasets.

Limitations:

- The datasets are too small for strong generalization.
- The examples may overrepresent obvious phishing language.
- The text model may learn simple keyword patterns instead of deeper context.
- The URL model may overvalue structural features that are not always malicious.
- The log rules may not represent real enterprise traffic patterns.

Responsible improvement steps:

- Use larger permission-safe datasets.
- Check dataset licenses before use.
- Remove personal or sensitive data.
- Include diverse legitimate and phishing examples.
- Evaluate with precision, recall, F1-score, and confusion matrices.
- Report limitations honestly.

## Adversarial evasion

Attackers may try to bypass phishing and anomaly detection systems by changing wording, domains, formatting, or behavior.

Examples of evasion risks:

- Avoiding suspicious words like `urgent` or `verify`.
- Using HTTPS on malicious sites.
- Using compromised legitimate websites.
- Shortening URLs or using redirects.
- Sending low-volume requests to avoid repeated-error thresholds.
- Mimicking normal browser User-Agent strings.

This project is not designed to defeat advanced evasion. It is a beginner defensive learning tool.

## Human review requirement

The system should never be the only decision-maker. A human reviewer should:

- Check the original message, URL, or log context.
- Review the model confidence and reasons.
- Verify whether the user expected the message or request.
- Avoid clicking suspicious URLs during investigation.
- Escalate unclear findings to a teacher, mentor, or authorized security team.

## Safe deployment guidance

This project is intended for local demos and college submissions. If someone extends it, they should:

- Restrict CORS origins instead of allowing all origins.
- Add authentication before exposing APIs outside localhost.
- Add rate limiting and input size controls.
- Avoid storing sensitive submitted content.
- Protect API keys using environment variables or a secrets manager.
- Log only safe metadata, not private message content.
- Add tests and monitoring before any real deployment.

## Conclusion

This project demonstrates a defensive, privacy-aware workflow for AI-assisted phishing analysis and log triage. It is useful for learning how offline training, saved models, real-time APIs, optional reputation checks, local monitoring, and responsible-use documentation fit together. Its outputs are educational signals only and must be combined with human judgment.
