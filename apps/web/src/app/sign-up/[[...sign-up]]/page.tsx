import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <p>Configure NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY para habilitar o cadastro.</p>;
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
      <SignUp />
    </main>
  );
}
