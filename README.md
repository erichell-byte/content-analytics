# Content Analytics

Personal, read-only social media metrics collected privately on macOS.
The GitHub Pages website is informational; it does not store credentials,
authorize visitors, or expose collected reports.

- [YouTube collector](youtube/README.md): channel validation, daily channel metrics,
  video counters and a private local daily scheduler.
- [TikTok collector](tiktok/README.md): Desktop OAuth, Sandbox user validation,
  profile/public-video lifetime counters and an independent private scheduler.

OAuth clients, tokens, user identities and all collected snapshots stay outside
Git. No private data or credentials are needed for automated tests.

TikTok Sandbox access is separate from production app review. Production
publication requires an accurate demo and policies matching the final service.
