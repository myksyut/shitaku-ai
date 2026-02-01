/**
 * Agent Avatar component - gives each AI agent a friendly, personified appearance
 */

type AvatarSize = 'sm' | 'md' | 'lg'

interface AgentAvatarProps {
  name: string
  size?: AvatarSize
  className?: string
}

// Emoji set for agent avatars - warm and approachable
const AGENT_EMOJIS = ['🤖', '🦊', '🐻', '🦁', '🐼', '🦉', '🐸', '🦋', '🌸', '✨', '💫', '🌟', '🎯', '📋', '💬']

// Get a consistent emoji based on agent name
function getAgentEmoji(name: string): string {
  const hash = name.split('').reduce((acc, char) => {
    return char.charCodeAt(0) + ((acc << 5) - acc)
  }, 0)
  const index = Math.abs(hash) % AGENT_EMOJIS.length
  return AGENT_EMOJIS[index]
}

const sizeClasses: Record<AvatarSize, string> = {
  sm: 'agent-avatar-sm',
  md: 'agent-avatar',
  lg: 'agent-avatar-lg',
}

export function AgentAvatar({ name, size = 'md', className = '' }: AgentAvatarProps) {
  const emoji = getAgentEmoji(name)

  return (
    <div className={`${sizeClasses[size]} ${className}`.trim()} role="img" aria-label={`${name}のアバター`}>
      {emoji}
    </div>
  )
}
