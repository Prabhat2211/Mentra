interface FeedbackBannerProps {
  type: 'success' | 'error';
  message: string;
  onDismiss?: () => void;
}

export default function FeedbackBanner({ type, message, onDismiss }: FeedbackBannerProps) {
  return (
    <div
      className={`mb-4 p-3 rounded-lg text-sm flex justify-between items-center ${
        type === 'success'
          ? 'bg-green-50 text-green-700 border border-green-200'
          : 'bg-red-50 text-red-700 border border-red-200'
      }`}
    >
      <span>{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="ml-2 text-sm font-medium hover:underline">
          Dismiss
        </button>
      )}
    </div>
  );
}
