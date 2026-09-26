export default function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-zinc-300">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-600 border-t-yellow-400" />
      {label}
    </span>
  );
}
