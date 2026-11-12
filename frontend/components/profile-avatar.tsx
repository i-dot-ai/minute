// This will be migrated to the design kit

import { User } from 'lucide-react'
import { ReactNode } from 'react'

const ProfileAvatar = ({
  children,
  fullName,
  size = 'medium',
}: {
  children?: ReactNode
  fullName?: string
  size?: 'small' | 'medium' | 'large'
}) => {
  const initials = fullName
    ?.split(' ')
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()

  return (
    <div className={`iai-avatar iai-avatar--${size}`}>
      {children || initials || (
        <User className={size === 'large' ? 'size-10' : 'size-5'} />
      )}
    </div>
  )
}

export default ProfileAvatar
