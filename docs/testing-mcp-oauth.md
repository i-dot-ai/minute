# Testing the MCP OAuth flow with curl

> [!WARNING]
> This is clauded so tread with caution. Its all a WIP until we get a client of our own to config and test.

End to end, by hand. Needs a client registered at
<https://sso.service.security.gov.uk/manage> with redirect URI
`<MCP_SERVER_URL>/auth/callback`, and `MCP_OIDC_CLIENT_ID` /
`MCP_OIDC_CLIENT_SECRET` set on the server.

```bash
B=http://localhost:8080          # wherever MCP_SERVER_URL points
IA=https://sso.service.security.gov.uk
```

### 0. Which mode is the server in?

```bash
curl -sL -o /dev/null -w '%{http_code}\n' $B/.well-known/oauth-protected-resource/mcp
```

`200` is OAuth. `404` means it is still on the bearer-token fallback — set the
credentials and restart before going further.

### 1. Are the credentials and redirect URI actually registered?

```bash
curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=authorization_code \
  -d code=not-a-real-code -d redirect_uri="$B/mcp/auth/callback" $IA/oauth2/token
```

| Response | Meaning |
|---|---|
| `invalid_grant` | both fine — the code was junk, as intended |
| `invalid_client` | wrong secret, or not an Internal Access client |
| `invalid_request` about `redirect_uri` | the URI is not registered |

### 2. A PKCE pair

Generate one. Never reuse a published pair: the verifier is the whole
protection, and a value from a spec or a blog post offers none.

```bash
V=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
C=$(python3 -c "
import base64, hashlib, sys
print(base64.urlsafe_b64encode(hashlib.sha256(sys.argv[1].encode()).digest()).rstrip(b'=').decode())" "$V")
```

### 3. Register a client

Our proxy answers this. Internal Access never learns it exists.

```bash
CID=$(curl -s -X POST $B/mcp/register -H 'Content-Type: application/json' -d '{
  "client_name":"curl","redirect_uris":["http://localhost:33418/callback"],
  "grant_types":["authorization_code"],"response_types":["code"],
  "token_endpoint_auth_method":"none"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['client_id'])")
```

### 4. Sign in

Start something listening for the redirect, then open the URL in a browser,
approve consent and sign in as normal.

```bash
nc -l 33418 &     # or just read the code from the browser's address bar

echo "$B/mcp/authorize?response_type=code&client_id=$CID\
&redirect_uri=http%3A%2F%2Flocalhost%3A33418%2Fcallback\
&code_challenge=$C&code_challenge_method=S256&state=xyz\
&scope=openid+email+profile"
```

The browser ends on `localhost:33418/callback?code=…`. The page will not load
— that is fine, the code is in the URL.

### 5. Swap the code for a token

At **our** token endpoint, not Internal Access's.

```bash
TOKEN=$(curl -s -X POST $B/mcp/token \
  -d grant_type=authorization_code -d "code=<from the address bar>" \
  -d "client_id=$CID" -d redirect_uri=http://localhost:33418/callback \
  -d "code_verifier=$V" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
```

### 6. Call a tool — the step that matters

```bash
curl -s -X POST $B/mcp/ -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"list_transcripts","arguments":{}}}'
```

This is the first time an Internal Access token reaches the Auth API, and it is
the one thing local testing cannot fake:

- **transcripts** — the whole chain works.
- **401 here, after step 5 succeeded** — the OAuth flow is fine and the Auth API
  refused the token. `/tokens/authorise` appears to accept only ALB-signed
  `x-amzn-oidc-data`. That is a question for the platform team, not a bug here.

Locally the answer is not meaningful either way: `ENVIRONMENT=local`
short-circuits the Auth API to a dummy user. Run this against dev to learn
anything.
