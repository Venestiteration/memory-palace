interface ErrorMessageProps {
  message: string;
}

export default function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <div className="mx-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-red-400">
      {message}
    </div>
  );
}