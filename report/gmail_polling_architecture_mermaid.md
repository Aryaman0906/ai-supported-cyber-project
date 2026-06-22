# Gmail Polling Architecture Mermaid Diagram

This diagram documents the actual submitted Gmail automation flow for Moodify / AI-Supported Cyber Project.

```mermaid
flowchart TD
    A[Windows Task Scheduler] --> B[run_gmail_poll_hidden.vbs]
    B --> C[run_gmail_poll_once.bat]
    C --> D[api.gmail_poll_worker]

    D --> E[Gmail OAuth credentials / local token store]
    D --> F[Gmail API]

    F --> G[Fetch recent INBOX messages]
    G --> H[parse_gmail_message in api/gmail_client.py]
    H --> I[GmailRiskEngine]
    I --> J[Text model + URL model + rules]
    J --> K[Risk result: low / medium / high / unknown]

    K --> L[Gmail labels]
    K --> M[LocalJsonStorage]

    M --> R[api.report_writer]
    R --> N[Markdown report]
    R --> O[CSV report]
    R --> P[XLSX report]

    N --> Q[Optional Google Drive upload]
    O --> Q
    P --> Q
```

The diagram intentionally shows near-real-time scheduled local polling. It does not describe full Gmail push monitoring or a fully cloud-native Cloud Run/Pub/Sub deployment.
