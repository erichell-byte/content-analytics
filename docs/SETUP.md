# Content Analytics setup

The GitHub Pages site is a static **landing page**. Private TikTok Sandbox collection on macOS is implemented separately; see [the collector setup](../tiktok/README.md). The website does not perform OAuth or publish private data.

## Publish site
1. GitHub repository → Settings → Pages.
2. Build and deployment → Deploy from a branch.
3. Branch: main; folder: /(root); Save.
4. Public site: https://erichell-byte.github.io/content-analytics/

TikTok Developer Portal URLs after publication:
- Website: https://erichell-byte.github.io/content-analytics/
- Terms: https://erichell-byte.github.io/content-analytics/terms.html
- Privacy: https://erichell-byte.github.io/content-analytics/privacy.html

**Before submission:** Replace preliminary policy language with accurate, complete details including the operator's contact method and real token/data handling. Ensure the app and demo video show a functioning, authorized sandbox integration. Don't submit the landing page as a completed integration.

## Security
GitHub Pages cannot securely handle an OAuth client secret. The local Desktop collector performs PKCE authorization-code exchange on the Mac, stores tokens outside Git, and uses a registered loopback callback. A future web service requires its own secure backend and registered web redirect URI. Never commit TikTok credentials, access tokens or refresh tokens. The repository is public.

The local collector requests user.info.basic, user.info.profile, user.info.stats and video.list. Sandbox configuration and target-user access must be enabled in the developer portal. No posting permissions are needed.
