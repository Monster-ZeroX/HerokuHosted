import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Torrent2Drive | Liquid Glass UI',
  description: 'Streamlined torrent-to-cloud experience with a glassy Next.js UI.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="main-shell">
          {children}
        </div>
      </body>
    </html>
  );
}
