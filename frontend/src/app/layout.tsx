import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinResearch AI",
  description: "AI-powered financial research",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
