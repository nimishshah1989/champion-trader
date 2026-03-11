"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const NAV_ITEMS = [
  { title: "Dashboard", href: "/", icon: "LayoutDashboard" },
  { title: "Scanner", href: "/scanner", icon: "Search" },
  { title: "Watchlist", href: "/watchlist", icon: "Eye" },
  { title: "Actions", href: "/actions", icon: "Zap" },
  { title: "Calculator", href: "/calculator", icon: "Calculator" },
  { title: "Trades", href: "/trades", icon: "TrendingUp" },
  { title: "Journal", href: "/journal", icon: "BookOpen" },
  { title: "Market Stance", href: "/market-stance", icon: "BarChart3" },
  { title: "Performance", href: "/performance", icon: "LineChart" },
  { title: "Simulation", href: "/simulation", icon: "FlaskConical" },
  { title: "Methodology", href: "/methodology", icon: "GraduationCap" },
] as const;

const INTELLIGENCE_ITEMS = [
  { title: "Intelligence", href: "/intelligence", icon: "Brain" },
  { title: "Optimize", href: "/intelligence/optimize", icon: "FlaskConical" },
  { title: "Shadow", href: "/intelligence/shadow", icon: "Ghost" },
  { title: "Attribution", href: "/intelligence/attribution", icon: "Target" },
] as const;

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-3">
        <h1 className="text-lg font-bold tracking-tight">CTS</h1>
        <p className="text-xs text-muted-foreground">Champion Trader System</p>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={item.href}>
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Intelligence</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {INTELLIGENCE_ITEMS.map((item) => {
                const isActive =
                  item.href === "/intelligence"
                    ? pathname === "/intelligence"
                    : pathname.startsWith(item.href);
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={item.href}>
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
