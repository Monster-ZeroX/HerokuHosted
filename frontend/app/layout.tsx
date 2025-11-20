import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DirectTorrent.me',
  description: 'Fast torrent and Mega.nz to cloud with priority speed for paid users.',
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
