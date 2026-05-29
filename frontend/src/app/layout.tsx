import type { Metadata } from "next";
import { Fira_Sans, Fira_Code } from "next/font/google";
import "./globals.css";

const firaSans = Fira_Sans({
  variable: "--font-fira-sans",
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

const firaCode = Fira_Code({
  variable: "--font-fira-code",
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Cognitive Face Live — Reconnaissance faciale temps réel",
  description:
    "Tableau de bord de reconnaissance faciale 1:N en temps réel : flux caméra, télémétrie head-pose, historique et gestion des visages de référence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="fr"
      className={`${firaSans.variable} ${firaCode.variable} h-full antialiased`}
      style={{ fontFamily: "var(--font-fira-sans)" }}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
