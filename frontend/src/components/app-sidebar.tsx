"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { SettingsButton } from "@/components/settings-drawer";

const CORE_NAV = [
  { title: "Dashboard", href: "/" },
  { title: "Pipeline", href: "/pipeline" },
  { title: "Trades", href: "/trades" },
  { title: "Review", href: "/review" },
] as const;

const STRATEGIES_NAV = [
  { title: "RS EMA50×200", href: "/rs-strategy" },
  { title: "Strategy Guide", href: "/strategy-guide" },
] as const;

const INTELLIGENCE_NAV = [
  { title: "Intelligence", href: "/intelligence" },
  { title: "Attribution", href: "/intelligence/attribution" },
] as const;

function isActive(href: string, pathname: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/intelligence") return pathname === "/intelligence";
  return pathname.startsWith(href);
}

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-3">
        <h1 className="text-lg font-bold tracking-tight">CTS</h1>
        <p className="text-xs text-muted-foreground">Champion Trader System</p>
      </SidebarHeader>

      <SidebarContent>
        {/* Core Trading */}
        <SidebarGroup>
          <SidebarGroupLabel>Trading</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {CORE_NAV.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={isActive(item.href, pathname)}>
                    <Link href={item.href}>
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Strategies */}
        <SidebarGroup>
          <SidebarGroupLabel>Strategies</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {STRATEGIES_NAV.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={isActive(item.href, pathname)}>
                    <Link href={item.href}>
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Intelligence */}
        <SidebarGroup>
          <SidebarGroupLabel>Intelligence</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {INTELLIGENCE_NAV.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={isActive(item.href, pathname)}>
                    <Link href={item.href}>
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Settings</span>
          <SettingsButton />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
