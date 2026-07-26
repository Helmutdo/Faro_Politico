import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trama Pública",
  description: "Transparencia parlamentaria con fuentes oficiales verificables.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
