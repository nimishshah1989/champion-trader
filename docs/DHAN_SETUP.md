# Dhan Broker API Setup

Dhan integration — Phase 6.

Steps:
1. Create a Dhan trading account at dhan.co
2. Enable API access in Dhan settings
3. Generate API credentials (Client ID + Access Token)
4. Add credentials to `.env` file:
   - `DHAN_CLIENT_ID=your_client_id`
   - `DHAN_ACCESS_TOKEN=your_access_token`
5. Test connection via the `/health` endpoint
