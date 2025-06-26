import React from 'react';
import { ButtonProps } from './Button.types';
import LoadingSpinner from '../LoadingSpinner';

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  children,
  onClick,
  type = 'button',
  className = '',
  icon,
  iconPosition = 'left',
  fullWidth = false,
  'data-testid': testId,
}) => {
  const baseClasses = 
    'font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 ' +
    'transition-all duration-200 touch-manipulation inline-flex items-center justify-center ' +
    'min-h-[44px] gap-2';

  const variantClasses = {
    primary: 
      'bg-gradient-to-r from-indigo-500 to-purple-500 text-white ' +
      'hover:from-indigo-600 hover:to-purple-600 hover:scale-105 ' +
      'focus:ring-indigo-300 focus:ring-opacity-50 ' +
      'shadow-xl hover:shadow-2xl',
    secondary: 
      'bg-white text-indigo-700 border border-indigo-200 ' +
      'hover:bg-indigo-100 hover:scale-105 ' +
      'focus:ring-indigo-300 focus:ring-opacity-50 ' +
      'shadow-md hover:shadow-lg',
    glass: 
      'bg-white bg-opacity-20 backdrop-blur-sm text-white ' +
      'hover:bg-opacity-30 hover:scale-105 ' +
      'focus:ring-white focus:ring-opacity-50 ' +
      'shadow-lg hover:shadow-xl',
    ghost: 
      'text-indigo-600 bg-transparent ' +
      'hover:text-indigo-800 hover:bg-indigo-50 ' +
      'focus:ring-indigo-300 focus:ring-opacity-50',
    danger: 
      'bg-red-500 text-white ' +
      'hover:bg-red-600 hover:scale-105 ' +
      'focus:ring-red-300 focus:ring-opacity-50 ' +
      'shadow-md hover:shadow-lg',
    success: 
      'bg-green-500 text-white ' +
      'hover:bg-green-600 hover:scale-105 ' +
      'focus:ring-green-300 focus:ring-opacity-50 ' +
      'shadow-md hover:shadow-lg',
    teal: 
      'bg-teal-500 text-white ' +
      'hover:bg-teal-600 hover:scale-105 ' +
      'focus:ring-teal-300 focus:ring-opacity-50 ' +
      'shadow-md hover:shadow-lg',
    outline: 
      'border-2 border-indigo-500 text-indigo-500 bg-transparent ' +
      'hover:bg-indigo-500 hover:text-white hover:scale-105 ' +
      'focus:ring-indigo-300 focus:ring-opacity-50',
  };

  const sizeClasses = {
    xs: 'px-2 py-1 text-xs rounded min-h-[32px]',
    sm: 'px-3 py-2 text-sm rounded-lg min-h-[36px]',
    md: 'px-4 py-3 text-base rounded-xl min-h-[44px]',
    lg: 'px-6 py-4 text-lg rounded-2xl min-h-[52px]',
    xl: 'px-8 py-5 text-xl rounded-2xl min-h-[60px]',
  };

  const disabledClasses = 'disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none';
  const fullWidthClass = fullWidth ? 'w-full' : '';

  const combinedClasses = `
    ${baseClasses}
    ${variantClasses[variant]}
    ${sizeClasses[size]}
    ${disabledClasses}
    ${fullWidthClass}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  const renderContent = () => {
    if (loading) {
      return (
        <>
          <LoadingSpinner size={size === 'xs' || size === 'sm' ? 'xs' : 'sm'} />
          <span>Loading...</span>
        </>
      );
    }

    const iconElement = icon && (
      <span className="flex-shrink-0">
        {icon}
      </span>
    );

    if (iconPosition === 'right') {
      return (
        <>
          <span>{children}</span>
          {iconElement}
        </>
      );
    }

    return (
      <>
        {iconElement}
        <span>{children}</span>
      </>
    );
  };

  return (
    <button
      type={type}
      className={combinedClasses}
      onClick={onClick}
      disabled={disabled || loading}
      data-testid={testId}
    >
      {renderContent()}
    </button>
  );
};

export default Button;