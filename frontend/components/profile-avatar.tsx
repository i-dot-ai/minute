// This will be migrated to the design kit

import { User } from 'lucide-react'
import { ReactNode } from 'react'

const ProfileAvatar = ({
  children,
  fullName,
  size = 'medium',
  inverse = false,
}: {
  children?: ReactNode
  fullName?: string
  size?: 'small' | 'medium' | 'large'
  inverse?: boolean
}) => {
  const initials = fullName
    ?.split(' ')
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()

  let sizeClass = ''
  switch (size) {
    case 'large':
      sizeClass = 'size-10'
      break
    case 'small':
      sizeClass = 'size-4'
    default:
      sizeClass = 'size-5'
  }

  return (
    <div
      className={`iai-avatar iai-avatar--${size} ${inverse ? 'iai-avatar--inverse' : ''}`}
    >
      {children || initials || <User className={sizeClass} />}
    </div>
  )
}

export default ProfileAvatar
