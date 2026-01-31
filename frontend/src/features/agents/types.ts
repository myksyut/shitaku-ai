/**
 * Agent feature type definitions
 */

export interface Agent {
  id: string
  name: string
  description: string | null
  slack_channel_id: string | null
  created_at: string
  updated_at: string | null
}

export interface AgentCreate {
  name: string
  description?: string | null
  slack_channel_id?: string | null
}

export interface AgentUpdate {
  name?: string
  description?: string | null
  slack_channel_id?: string | null
}
