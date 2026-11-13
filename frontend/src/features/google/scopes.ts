export function hasCalendarReadScope(grantedScopes: readonly string[]) {
  return grantedScopes.includes('https://www.googleapis.com/auth/calendar.readonly')
}
