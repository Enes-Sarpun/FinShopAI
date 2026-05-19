"use client";
import dynamic from "next/dynamic";

interface SidebarProps {
  userName?: string;
  userEmail?: string;
}

const SidebarInner = dynamic(() => import("./SidebarInner"), { ssr: false });

export default function Sidebar({ userName, userEmail }: SidebarProps) {
  return <SidebarInner userName={userName} userEmail={userEmail} />;
}
