# Content Analytics setup

The GitHub Pages site is a static **landing page**, not an active TikTok integration.

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
GitHub Pages cannot securely handle an OAuth client secret. Implement TikTok OAuth with PKCE and server-side authorization-code exchange, store tokens only in protected backend storage, and register the backend redirect URI after its hosting is known. Never commit TikTok credentials, access tokens or refresh tokens. The repository is public.

The intended Display API scope is video.list and user.info.basic; available endpoints and approvals must be validated in the developer portal.
