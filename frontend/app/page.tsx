import Link from 'next/link';

export default function HomePage() {
  return (
    <main>
      <h1 className="hero-title">DirectTorrent.me</h1>
      <p className="hero-subtitle">
        Seamless torrent and Mega.nz delivery to your cloud. Paid members enjoy priority speed and priority support while free
        users stay on the community tier.
      </p>
      <div className="hero-actions" style={{ marginTop: 24 }}>
        <Link className="button-primary" href="/register">
          Create account
        </Link>
        <Link className="button-ghost" href="/login">
          Log in
        </Link>
      </div>
    </main>
  );
}
