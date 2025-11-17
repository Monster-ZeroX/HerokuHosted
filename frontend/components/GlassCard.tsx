import { ReactNode } from 'react';

interface GlassCardProps {
  title?: string;
  icon?: string;
  action?: ReactNode;
  children: ReactNode;
}

export function GlassCard({ title, icon, action, children }: GlassCardProps) {
  return (
    <div className="glass" style={{ padding: '22px 24px', borderImage: 'linear-gradient(135deg, rgba(255,255,255,0.3), rgba(255,255,255,0)) 1' }}>
      {(title || action) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, gap: 12 }}>
          {title && (
            <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 10, margin: 0 }}>
              {icon && <span className="icon">{icon}</span>}
              <span>{title}</span>
            </h3>
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
