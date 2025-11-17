import { ReactNode } from 'react';

interface GlassCardProps {
  title?: string;
  icon?: string;
  action?: ReactNode;
  children: ReactNode;
}

export function GlassCard({ title, icon, action, children }: GlassCardProps) {
  return (
    <div className="glass" style={{ padding: '20px 22px' }}>
      {(title || action) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          {title && (
            <h3 className="card-title">
              {icon && <span className="icon">{icon}</span>}
              {title}
            </h3>
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
