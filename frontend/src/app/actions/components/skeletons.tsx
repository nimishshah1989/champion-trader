import { Skeleton } from "@/components/ui/skeleton";

export function AlertCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-6 w-20 bg-slate-100 rounded" />
        <Skeleton className="h-5 w-28 bg-slate-100" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-10 bg-slate-100 rounded" />
        <Skeleton className="h-10 bg-slate-100 rounded" />
        <Skeleton className="h-10 bg-slate-100 rounded" />
      </div>
      <div className="grid grid-cols-4 gap-2">
        <Skeleton className="h-8 bg-slate-100 rounded" />
        <Skeleton className="h-8 bg-slate-100 rounded" />
        <Skeleton className="h-8 bg-slate-100 rounded" />
        <Skeleton className="h-8 bg-slate-100 rounded" />
      </div>
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-8 w-24 bg-slate-100 rounded" />
        <Skeleton className="h-8 w-20 bg-slate-100 rounded" />
      </div>
    </div>
  );
}

export function SectionSkeleton({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <AlertCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function EmptyState({ message, icon }: { message: string; icon: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-10 text-center col-span-full">
      <div className="text-4xl mb-3 text-slate-300">{icon}</div>
      <p className="text-sm text-slate-400">{message}</p>
    </div>
  );
}
