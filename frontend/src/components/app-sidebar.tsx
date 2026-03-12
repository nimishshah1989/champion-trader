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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight } from "lucide-react";

const CORE_NAV = [
  { title: "Dashboard", href: "/" },
  { title: "Pipeline", href: "/pipeline" },
  { title: "Actions", href: "/actions" },
  { title: "Trades", href: "/trades" },
  { title: "Review", href: "/review" },
] as const;

const ADVANCED_NAV = [
  { title: "Simulation", href: "/simulation" },
] as const;

const INTELLIGENCE_NAV = [
  { title: "Intelligence", href: "/intelligence" },
  { title: "Optimize", href: "/intelligence/optimize" },
  { title: "Shadow", href: "/intelligence/shadow" },
  { title: "Attribution", href: "/intelligence/attribution" },
  { title: "How It Works", href: "/intelligence/guide" },
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

        {/* Advanced — collapsed by default */}
        <Collapsible defaultOpen={false} className="group/collapsible">
          <SidebarGroup>
            <CollapsibleTrigger className="flex w-full items-center justify-between px-2 py-1.5 text-xs font-medium text-sidebar-foreground/60 hover:text-sidebar-foreground/80">
              <span>Advanced</span>
              <ChevronRight className="h-3.5 w-3.5 transition-transform group-data-[state=open]/collapsible:rotate-90" />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarGroupContent>
                <SidebarMenu>
                  {ADVANCED_NAV.map((item) => (
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
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>

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
