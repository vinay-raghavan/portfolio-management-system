import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">Portfolio Management System</h1>
        <p className="text-muted-foreground mb-8">
          Track your investments, analyze performance, and execute trades
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/login"
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="px-6 py-3 border border-border rounded-lg hover:bg-accent"
          >
            Register
          </Link>
        </div>
      </div>
    </main>
  );
}

