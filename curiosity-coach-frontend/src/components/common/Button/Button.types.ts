import { ReactNode } from 'react';

export type ButtonVariant = 
  | 'primary' 
  | 'secondary' 
  | 'glass' 
  | 'ghost' 
  | 'danger' 
  | 'success' 
  | 'teal'
  | 'outline';

export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
  'data-testid'?: string;
}