"use client";

import * as React from "react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { getGlossaryEntry, getFullTerm } from "@/lib/glossary";

interface InfoTooltipProps {
  termKey: string;
  showFullTerm?: boolean;
  children?: React.ReactNode;
}

const INFO_ICON_CLASS =
  "inline-flex items-center justify-center w-3.5 h-3.5 rounded-full border border-slate-300 text-[9px] text-slate-400 italic cursor-help ml-0.5";

function InfoIcon() {
  return <span className={INFO_ICON_CLASS}>i</span>;
}

export function InfoTooltip({ termKey, showFullTerm, children }: InfoTooltipProps) {
  const entry = getGlossaryEntry(termKey);
  const label = getFullTerm(termKey);

  const trigger = children ? (
    <span className="cursor-help">{children}</span>
  ) : showFullTerm ? (
    <span className="inline-flex items-center gap-0.5">
      <span className="text-sm text-slate-700">{label}</span>
      <InfoIcon />
    </span>
  ) : (
    <InfoIcon />
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>{trigger}</TooltipTrigger>
      <TooltipContent
        side="top"
        className="bg-white border border-slate-200 shadow-sm px-3 py-2 rounded-lg"
      >
        <div className="max-w-[280px] text-left">
          <p className="font-semibold text-xs text-slate-800">{label}</p>
          {entry && (
            <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">
              {entry.definition}
            </p>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
