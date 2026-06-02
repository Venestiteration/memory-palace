export default function LoadingSpinner({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className={`${className} animate-spin rounded-full border-2 border-border border-t-accent`} />
    </div>
  );
}