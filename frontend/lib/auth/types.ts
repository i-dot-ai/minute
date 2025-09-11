export type DecodedKeycloakToken = {
  sub: string
  iss: string
  aud: string
  typ: string
  azp: string
  session_state: string
  acr: string
  'allowed-origins': string[]
  realm_access: {
    roles: string[] | undefined
  }
  resource_access: {
    account: {
      roles: string[]
    }
  }
  scope: string
  sid: string
  email_verified: boolean
  name: string
  preferred_username: string
  given_name: string
  family_name: string
  email: string
  auth_time: number
  exp: number
  iat: number
  jti: string
}

export type ParsedAuthTokenResult = {
  email: string
  roles: string[]
}
