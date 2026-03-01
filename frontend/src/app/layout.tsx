import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Champion Trader System",
  description: "Swing trading intelligence platform — Champion Trader methodology",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <SidebarProvider>
          <AppSidebar />
          <SidebarInset>
            <header className="flex h-14 items-center gap-2 border-b px-4">
              <SidebarTrigger />
            </header>
            <main className="flex-1 p-6">{children}</main>
          </SidebarInset>
        </SidebarProvider>
      </body>
    </html>
  );
}
