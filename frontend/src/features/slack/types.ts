export interface SlackIntegration {
  id: string
  workspace_id: string
  workspace_name: string
  created_at: string
}

export interface SlackChannel {
  id: string
  name: string
}

export interface SlackMessage {
  user_name: string
  text: string
  posted_at: string
}

export interface SlackOAuthStartResponse {
  authorize_url: string
}
